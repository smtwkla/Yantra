```
Step: S062 — Filter the equipment list by property
Doc: impl-report
Author: Coder (Opus)
Date: 27-10-2026
```

# S062 — Implementation report

The equipment list and the printed asset list now filter by property. A user builds lines of
*property, operator, value* in a dialog, joined by *All conditions* or *Any condition*. The brief
is built as written, with one departure: applying and clearing the property filter add a history
step (`router.push`), so *Back* brings back a cleared filter (D-1 below). All unit suites are
green, and so are the targeted and whole-suite browser runs.

## 1. What was built

- **Button *Filter by property*** in the list's filter row, after the search box. With a filter
  set it reads *Properties (2)* and is filled (`btn-primary`).
- **Dialog *Filter by property*** (`PropertyFilterModal.vue`):
  - one bordered block per condition: the property select (with the bin button *Remove
    condition* at its right), then the operator and the value;
  - *Match* (*All conditions* / *Any condition*) above the lines, shown from two lines;
  - *Add condition*, which turns into "10 conditions at most" at 10 lines;
  - "Machines with no value are not included." under a *not equal to* or *is not* line;
  - *Apply filter* is disabled while a line has no property or misses its value. The reason,
    "Complete or remove the empty condition", shows as its tooltip and, on a phone, as a line
    under the conditions;
  - *Apply filter* sends the check request first. A refusal shows under its line, and the
    dialog stays open.
- **The filter line** under the filter row, whenever the URL has `props`: "Properties: Rated
  power more than 7.5 kW", or "Properties (all of): … · …" / "Properties (any of): … · …", with
  the ✕ button *Clear property filter*. A tap on the text opens the dialog.
- **An unreadable `props`** (a cut or hand-edited bookmark): the line reads "Properties: cannot
  be read". The list is not asked, and one message, "The property filter cannot be read. Clear it
  and make it again.", shows in place of the table, with no *Retry*.
- **The first property filter at the default level** also sets `level=all`, so the motors show.
- **The API**: `GET /api/equipment` and `GET /api/equipment/asset-list` take `props` and answer
  400 with the field of § 5.2 (`props`, `props.rules.<i>`, `props.rules.<i>.property_id` / `.op`
  / `.value`).
- **The printed asset list**: *Print asset list* carries `props`; the API applies it to the
  machines; parts still come with their machine; the section header names it ("Class: RPP ·
  Properties: Rated power more than 7.5 kW").

## 2. How it works

**Pure core, `backend/property_filter_core.py`** (no Flask, no database), in three steps:

1. `read_property_filter(raw)` checks the shape (checks 1–3): length at most 4000, JSON, an
   object, `match` `all`/`any` (missing = `all`), `rules` a list of at most 10, each rule an
   object with a positive whole `property_id` (a boolean is refused). It returns the rules and
   `property_ids`, the sorted set of ids. A missing or empty `props` gives no rules.
2. `check_property_filter(parsed, properties, options)` checks each line in turn (checks 4–6):
   the property found and active, the operator in `OPERATORS[data_type]`, the value by its
   operator. Numbers go through `properties_core.parse_value`, so the number messages are the
   property master's. It returns clean values: `Decimal`, a pair of `Decimal`s for *between*,
   option ids, trimmed text, 1/0.
3. `filter_condition(filter, like)` builds one SQL condition. Per line: *applies* (an `EXISTS`
   on `class_properties`, left out for an every-class property; `e.level = %s` with `GEO_LEVEL`
   for a Location), then the value in force, `COALESCE(own row's column, model row's column)`,
   then the operator's SQL from the fixed table `_COMPARE_SQL` (or `BETWEEN`, `IN`, `NOT IN`,
   `LIKE`, `IS [NOT] NULL`). Lines join with AND for `all` and OR for `any`. Column names come
   only from `_COLUMNS` (`VALUE_COLUMNS` plus `value_lat` for a Location). Every request value
   is a parameter.

**Shell.** `equipment._property_filter(cur)` calls the three steps, with
`properties.filter_properties(cur, ids)` between the first two (one plain read of the
properties and one of their options; none without ids), and raises `ApiError(message, 400,
field)` on the first refusal. `_list_filters(cur)` appends its condition. Both routes now build
their conditions inside the `with get_db().cursor()` block, before the unit-access check, so a
bad filter is 400 also for a user with no units (§ 5.5).

**Frontend.** `utils/propertyFilter.js` holds the operators and their words, `encodeFilter` /
`decodeFilter`, `ruleComplete`, `describeFilter` and `propsChanges` (the level rule). The
dialog keeps its own lines (a line splits its value into `value`, `low`/`high` and
`optionIds`), and turns them into rules on apply. `dirty` compares the rules with a snapshot made
at open, so FormModal's "Discard your changes?" guard applies. The dialog loads the properties
with `ensureProperties()` and, with a class filter on the list, intersects the active ones with
`GET /api/masters/equipment-classes/<id>/properties`. A line whose property is not in that list
shows it last. The check request is `GET /api/equipment?props=…&level=all&per_page=1`, with
`saving` passed to FormModal. A 400 whose field is `props.rules.<i>[.field]` goes under line *i*
(beside the property, the operator or the value), and the dialog scrolls it into view
(`revealError`). Any other failure shows at the top.

`EquipmentView.vue` adds `props` to `listUrl`, decodes it for the button, the line and the
unreadable case, and loads `ensureProperties()` only when the URL has `props`.
`assetList.js` adds `props` to `FILTER_KEYS`, and `filtersLabel` uses `describeFilter`, so the
header and the list say the same words. `AssetListPrintView.vue` loads the properties only when
the query has `props`.

## 3. Files touched

New:
- `backend/property_filter_core.py`: the pure core (read, check, SQL).
- `backend/tests/test_property_filter_core.py`: 72 core tests (§ 8.1).
- `backend/tests/test_property_filter_api.py`: 18 API tests (§ 8.2).
- `frontend/src/utils/propertyFilter.js`: the pure frontend helpers.
- `frontend/src/views/equipment/PropertyFilterModal.vue`: the dialog.
- `frontend/tests/propertyFilter.test.js`: the helpers' unit tests (§ 8.3).

Changed:
- `backend/equipment.py`: `_property_filter(cur)`; `_list_filters(cur)`; both routes build their
  conditions inside the cursor block, before the unit check.
- `backend/properties.py`: `filter_properties(cur, ids)`; cross-reference comments on
  `linked_properties` and `lock_value_properties` (BR1-11, BS1-06).
- `backend/properties_core.py`: cross-reference comment on `on_level` only.
- `backend/tests/conftest.py`: `Uniq.property_name(prefix)`; the shared fixtures
  `make_property(admin, uniq)`, `link(admin)`, `every_class(admin, make_property)`.
- `backend/tests/test_item_properties_api.py`: uses the shared fixtures; its `_numbers` counter,
  `make_property`, `link` and `every_class` removed; the one `every_class` call now names
  `data_type="yes_no"` (the shared fixture has no type default).
- `backend/tests/test_properties_api.py`: its own `every_class` removed (uses the shared one,
  which takes this module's `make_property`); its `make_property` and `link` stay.
- `frontend/src/views/EquipmentView.vue`: the button, the filter line, the unreadable case,
  `props` in `listUrl`, the level rule, the dialog; `update()` takes `{ push }`.
- `frontend/src/utils/assetList.js`: `props` in `FILTER_KEYS`; `filtersLabel` names the filter.
- `frontend/src/views/AssetListPrintView.vue`: `ensureProperties()` when the query has `props`;
  the properties passed to `filtersLabel`.
- `frontend/tests/assetList.test.js`: three new cases (`parseAssetListQuery`, `assetListPath`,
  `filtersLabel` with `props`).
- `frontend/e2e/equipment.spec.js`: seven S062 tests.
- `frontend/e2e/asset-list.spec.js`: one S062 test.
- `docs/Plan.MD`, `.claude/CLAUDE.md`: the docs pass (below).
- `docs/steps/INDEX.md`, `docs/steps/S062-property-filter/1-brief.md`: status only.

## 4. Decisions taken

- **D-1 (departure, behaviour the user sees): applying and clearing the property filter are
  history steps (`router.push`); the other filters still use `router.replace`.** The brief's
  check § 8.4 asks "Back after *Clear property filter* brings it back". With `replace`, as
  every other filter uses, *Back* would leave the list instead. A filter built in a dialog is
  also costlier to make again than a select. `update()` gained an option `{ push }`; nothing
  else uses it. If the user wants the list's one rule kept (`replace`), the § 8.4 check must
  change instead.
- **D-2:** The core checks line by line (checks 4, 5, 6 of line 1, then of line 2), so the first
  refusal is the first line's. The brief orders the checks but does not say whether by check or by
  line.
- **D-3:** `read_property_filter(None or "")` returns an empty filter rather than a third
  result. The shell then calls all three steps every time; `filter_properties` makes no query
  for no ids. This keeps one path.
- **D-4:** `json.loads` raises `RecursionError` for a deeply nested `[[[[…` within 4000
  characters. The core catches it as "cannot be read", so it is a 400, not a 500.
- **D-5:** A missing `rules` key is "cannot be read" (check 1, "rules not a list").
- **D-6:** In the filter line, a text value is quoted: `Frame size contains "IE3"`, so its
  spaces and start are clear. The brief shows no text example.
- **D-7:** Operator words: *equals*, *not equal to*, *less than*, *at most*, *more than*, *at
  least*, *between*, *is*, *is not*, *contains*, *has a value*, *has no value*. For text and
  yes/no, `eq` reads *is*, not *equals*. A choice line reads "Mobility is not Fixed or Mobile"
  for several options.
- **D-8:** The frontend's `decodeFilter` mirrors the backend's checks 1–3 (with more than 10
  lines also "cannot be read"). So a `props` the screen calls readable is sent, and a refusal
  from checks 4–6 (for example an inactive property in a bookmark) shows in the list's error box
  with its message.
- **D-9:** The yes/no value is a select with a disabled blank *Choose* first, then *Yes* /
  *No*, so a new line is not "complete" by default.
- **D-10:** The button sits right after the search box, inside the filter group, rather than
  beside the print buttons (which keep `ms-auto`). It is still before the print buttons.
- **D-11:** The shared `every_class` fixture takes `*args, **overrides` and passes them to the
  module's `make_property`, so it serves both signatures (`make_property(prefix, …)` and
  `test_properties_api.py`'s `make_property(**overrides)`). Its teardown runs as admin.
- **D-12:** A choice's inactive options show in the dialog, marked "(inactive)", after the
  active ones, as § 5.3 says; the backend accepts them (values may hold them).

## 5. Not done, deferred or assumed

- **Assumption:** The dialog's error under a line stays until the next *Apply filter* or until
  a line is removed. It does not clear while the user types.
- **Assumption:** The check request does not carry the list's other filters (class, unit,
  search): the brief names only `props`, `level=all` and `per_page=1`. So it checks the filter,
  not whether anything matches.
- **Not done (out of scope):** counts inside the dialog, saved filters, property columns.
- **Note:** The print page with an unreadable `props` shows the API's refusal in its error line
  (with its *Retry*), as § 5.5 says for the print page.

## Manual checks

- [auto] **important** An engineer filters the default list by a part's rated power; the level
  turns to *All levels*, only the motor shows, the line reads the condition, the URL has
  `props` and `level=all`, and *Clear property filter* brings the full list back —
  `frontend/e2e/equipment.spec.js::S062: engineer filters the default list by a part's rated power; the level widens and Clear brings the full list back`
- [auto] A hand-broken `props`: "Properties: cannot be read", the message once, no *Retry*;
  *Clear property filter* brings the list back —
  `frontend/e2e/equipment.spec.js::S062: a hand-broken props shows the line cannot be read and one message, and Clear brings the list back`
- [auto] **important** Two lines with *Any condition*: both machines show; with *All
  conditions*: none —
  `frontend/e2e/equipment.spec.js::S062: two lines with Any condition list both machines; with All conditions none`
- [auto] A value "7,5" is refused under its line with "Enter a number", and the dialog stays
  open — `frontend/e2e/equipment.spec.js::S062: a value 7,5 is refused under its line and the dialog stays open`
- [auto] A choice line *is not* shows "Machines with no value are not included." —
  `frontend/e2e/equipment.spec.js::S062: a choice line with is not says machines with no value are not included`
- [auto] Reload keeps the filter; Back after *Clear property filter* brings it back —
  `frontend/e2e/equipment.spec.js::S062: a reload keeps the filter, and Back after Clear property filter brings it back`
- [auto] *Print asset list* with a property filter lists only the matching machine, and its
  header reads "Properties: …" —
  `frontend/e2e/asset-list.spec.js::S062: Print asset list with a property filter lists only the matching machine and names the filter`
- [auto] `@device`: the dialog with three lines fits the screen, its buttons in view —
  `frontend/e2e/equipment.spec.js::S062: the Filter by property dialog with three lines fits the screen, its buttons in view`
  (phone-chromium and desktop-chromium)

On a real device: none (§ 8.5). No row added to `docs/steps/device-checks.md`.

## Tests

- **New tests alone** (one lane, `phone-chromium`, `-g S062`): first run 6 passed, 2 failed
  (both my test mistakes: the part's Path column holds its machine's code, and a null-valued
  option reads as its text); after the fix, 7 passed (equipment spec), the asset-list test
  having passed in the first run.
- **Targeted** (`e2e/equipment.spec.js e2e/asset-list.spec.js e2e/screens.spec.js`, Normal):
  65 passed, 1 skipped (the existing desktop skip of `screens.spec.js` "S040: the manager's
  bottom bar…"), 111 s.
- **All unit suites** (`YANTRA_TEST_RUN=s062c1 tooling/run-tests.bat`): backend 3261 passed,
  frontend 231 passed, tooling 185 passed.
- **Build check** (`npx vite build`): built; only the existing chunk-size warning.
- **Whole suite** (Normal, `tooling/run-e2e-tests.bat`): 231 passed, 7 skipped (existing skips), 238 tests on 6 lanes, 205 s; no failure.

## Docs updated

- `docs/Plan.MD` § 4.1 *Equipment class* paragraph: a "Built 27-10-2026 (S062, no migration)"
  sentence after the orchestrator's "Decided" one: the button, the dialog, `props` in the URL
  and the API, the filter line, the unreadable case, the print.
- `.claude/CLAUDE.md` § SMTW-Review: the spec-to-step map gains S062 under `equipment` and
  `asset-list`.
- `docs/schema.md`, `docs/schema.html`: none, because there is no migration.
- `docs/steps/device-checks.md`: none, because the step has no real-device check.

## Feedback

- hindrance: a Bash heredoc that appended two JS test blocks failed with "unexpected EOF while looking for matching `'`", and nothing was written; I redid it with the Edit tool (1 retry, about 2 min).
- waste: my two new browser tests failed on their first run, on test mistakes only (a part's Path column holds its parent's code; a `:value="null"` option reads as its text), which cost one extra run of the S062 tests (about 1 min).
- rule: the brief's check "Back after Clear property filter brings it back" conflicts with the list's rule that every filter uses `router.replace`; the brief review did not catch it, so the coder had to choose (D-1).

## Fix rounds

### Round 1

Source: `4-code-review-r1.md`. D-1 (`router.push`) is left as built; it is with the user.

- **CR1-01 Fixed.** `TestAssetList.test_a_user_with_no_units_gets_400_for_a_bad_filter` added in
  `backend/tests/test_property_filter_api.py`: a user with no units and `props={broken` gets 400
  `{"error": UNREADABLE, "field": "props"}`. It guards existing correct behaviour, so it passes
  on the code as built (no red run; a red run would need `_list_filters` moved below
  `accessible_unit_ids` in `asset_list`, which is the regression it guards against).
- **CR1-02 Fixed.** The yes/no value select's first option reads "Choose Yes or No".
- **CR1-03 Fixed.** `py-0` removed from the *Clear property filter* button in `EquipmentView.vue`.
- **CR1-04 Fixed.** `open()` in `PropertyFilterModal.vue` now sets the lines, takes the
  snapshot and opens the dialog first; the property and class reads then fill the lists. A read
  error still shows at the top of the dialog.
- **CR1-05 Fixed.** A comment on `_option_ids` in `property_filter_core.py` says that `any()` stops
  at the first bad id, so an unhashable value never reaches `i not in known`.
- **CR1-06 Fixed.** The `f` prefix is dropped from the first string of the `cur.execute` call in
  `backend/properties.py` (`filter_properties`).

Tests (`YANTRA_TEST_RUN=s062c2`):
- targeted backend (`test_property_filter_api`, `_core`, `test_properties_api`): 140 passed;
- all suites once: backend 3262 passed, frontend 231 passed, tooling 185 passed;
- `npx vite build`: built, only the existing chunk-size warning;
- browser, targeted (`equipment`, `asset-list`, `screens` at Normal): 65 passed, 1 skipped
  (existing skip); this covers the dialog open (CR1-04) and the Clear button (CR1-03).

Docs updated: none, because the fixes change a button label, a spacing class, load order,
a comment and a test; no rule, API shape, secret or schema changed.

#### Feedback

- none

### Round 2

Source: `4-code-review-r2.md`. D-1 (`router.push`) is left as built.

- **CR2-01 Fixed.** `open()` in `PropertyFilterModal.vue` now keeps a copy of the starting match and
  lines (`initialMatch`, `initialLines`). `dirty` builds both the copy and the current state with
  `filterSnapshot(match, lines, dataTypeOf)` each time it is read, so both sides use the same data
  types, before and after the property list loads. To make this a pure, testable helper,
  `ruleOf` moved from the component to `propertyFilter.js` as `ruleOfLine(line, dataType)`, and
  `filterSnapshot` is new there.
  Test: `frontend/tests/propertyFilter.test.js`, `filterSnapshot (the dialog's dirty check, CR2-01)`
  (3 tests). Red before: the 3 tests failed because `filterSnapshot` did not exist (import
  undefined); the old component code is the same comparison with different data types, which the
  first test ("differs for the same lines before and after the property list loads") shows as the
  fault. Green after: 3 passed. No browser test: the fault needs the property list to arrive
  after the open, which the fast test backend does not allow.

Tests (`YANTRA_TEST_RUN=s062c3`):
- all suites once: backend 3262 passed, frontend 234 passed, tooling 185 passed;
- `npx vite build`: built, only the existing chunk-size warning;
- browser, targeted (`equipment`, `screens` at Normal): 61 passed, 1 skipped (existing skip).

Docs updated: none, because the fix changes how a dialog compares its state; no rule, API shape,
secret or schema changed.

#### Feedback

- none
