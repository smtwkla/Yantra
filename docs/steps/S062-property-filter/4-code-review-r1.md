```
Step: S062 — Filter the equipment list by property
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 27-10-2026
```

# S062 — Code review, round 1

**Verdict: no blocker or major finding is open.** The step is built as the brief says. The SQL
builder takes no request text into the SQL, and both routes refuse a bad filter before the
unit-access check. The shared fixtures moved as BS1-02 asks. I found two minor findings and four
nits. D-1 (`router.push` for the property filter) stays open for the user; my comment is in
§ D-1 below.

Reviewed: `git diff -w --ignore-cr-at-eol refs/steps/S061` (fb6a025) plus the untracked S062
files. I read `property_filter_core.py`, `PropertyFilterModal.vue`, `propertyFilter.js` and
`test_property_filter_api.py` in full, and every other touched file in its hunks and their
context (`equipment.py` `_list_filters`, `list_equipment`, `asset_list`; `EquipmentView.vue`
`load`, `filterKey`, the template's list states). I did not review S061's code.

## Tests

- **Unit suites** (`YANTRA_TEST_RUN=s062cr1 tooling/run-tests.bat`): backend PASSED, 3261
  passed (121 s); frontend PASSED, 231 passed (37 s); tooling PASSED, 185 passed.
- **Build check** (`npx vite build`): built; only the existing chunk-size warning.
- **Browser tests:** not re-run. No finding of mine needs one. The coder's runs stand:
  - targeted `equipment.spec.js`, `asset-list.spec.js`, `screens.spec.js` at Normal: 65 passed,
    1 skipped (an existing skip);
  - the whole suite once at Normal: 238 tests, 231 passed, 7 skipped (existing skips).
  These are the right specs: the step changed the equipment list and the asset list, plus
  `screens.spec.js`, which the settings always add.

## Findings

### CR1-01 (minor) — the check order of the asset list has no test

`backend/equipment.py:747` (`asset_list`), `backend/tests/test_property_filter_api.py:213`.

- **Problem.** Brief § 5.5 puts `_list_filters(cur)` before the unit-access check "in each
  route". `test_a_user_with_no_units_gets_400_for_a_bad_filter` checks this order for
  `GET /api/equipment` only. `TestAssetList.test_a_bad_filter_is_400` runs as admin, who has
  every unit, so it never reaches the early return for a user with no units.
- **Failure scenario.** A later change moves `_list_filters(cur)` in `asset_list` back below
  `accessible_unit_ids`, as it was before S062. A user with no units then gets
  `{"units": [], …}` with status 200 for a broken `props`. No test turns red.
- **Fix.** In `TestAssetList`, add the same check for `ASSET_LIST`: a user with no units and
  `props={broken` gets 400 with `{"error": UNREADABLE, "field": "props"}`.

### CR1-02 (minor) — "Choose" alone on the Yes / No value select

`frontend/src/views/equipment/PropertyFilterModal.vue:308`.

- **Problem.** The yes/no value select shows a disabled first option, "Choose" (D-9). "Choose"
  without an object does not say what to choose (scope B: say what the user sees). The other
  selects of the dialog name their object: "Choose a property".
- **Failure scenario.** A technician adds a line on a yes/no property such as "Has guard". The
  value box reads "Choose", and *Apply filter* stays disabled. The only hint is "Complete or
  remove the empty condition", which does not say that the box beside the operator is the
  missing part.
- **Fix.** Use "Choose Yes or No", the wording of the backend's `CHOOSE_YES_NO`, so the select
  and a refusal say the same thing.

## Nits

- **CR1-03** (nit) `frontend/src/views/EquipmentView.vue:340`: the ✕ *Clear property filter* is
  `btn-sm py-0`, about 24 px tall on a phone. It follows `TicketDetailView.vue:432`, but here it
  is the main way out of an unreadable filter. Drop `py-0`, so it has the height of the filter
  row's buttons.
- **CR1-04** (nit) `frontend/src/views/equipment/PropertyFilterModal.vue:132-145`: `open()`
  waits for `ensureProperties()` and the class request before the dialog shows. On a slow mobile
  network a tap on *Filter by property* shows nothing for a moment. Open the dialog first, or
  disable the button while it loads, as the other dialogs of the list do.
- **CR1-05** (nit) `backend/property_filter_core.py:136`: `any(…)` relies on short-circuit
  evaluation so that `i not in known` never sees an unhashable value (a dict in the list).
  Add a short comment that says so, or check `_is_whole_number` for every id first in its own
  `all(…)`.
- **CR1-06** (nit) `backend/properties.py:303`: the first string of the `cur.execute` call has
  an `f` prefix and no placeholder. Drop the `f` from that part.

## D-1 — `router.push` for the property filter (open for the user)

This is a comment, not a finding. The choice is the user's.

- **Fact.** Brief § 8.4 asks "Back after *Clear property filter* brings it back". Every other
  filter of the list uses `router.replace` (header comment of `EquipmentView.vue`). The two do
  not fit together: with `replace`, *Back* after *Clear* leaves the list. So the coder had to
  pick one, and reported the pick.
- **Fact.** As built, the code is correct for `push`. Apply and Clear each add one history
  entry. The level widening (§ 1 item 4a) is in the same entry as `props`, so one *Back* undoes
  both. The other filters keep `replace`. `filterKey` still clears the label ticks on each
  change. The test `S062: a reload keeps the filter, and Back after Clear property filter
  brings it back` checks it.
- **Consequence of each option.**
  - *Keep `push`* (as built): *Back* brings back a filter that took a dialog to build. The list
    then has two history rules: one for the property filter and one for the other filters.
  - *Use `replace`*: the list keeps one rule. The § 8.4 check and its test must change, and
    `update()` loses its `{ push }` option.
- **Either way.** `docs/Plan.MD` § 4.1 now says "applying and clearing it are steps of the
  browser's history". The header comment of `EquipmentView.vue` says so too. If the user picks
  `replace`, both texts must change in the fix round.

## Checked and found consistent

- **The SQL builder (ISO 27001 A.8.28).** No request text reaches the SQL. Column names come
  only from `_COLUMNS` (`VALUE_COLUMNS` plus `GEO_COLUMNS[0]`), keyed by the data type read from
  the database. Operator SQL comes only from `_COMPARE_SQL` and the fixed `BETWEEN`, `IN`,
  `NOT IN`, `LIKE` and `IS [NOT] NULL` texts. The `IN` placeholders are a count of fixed `%s`.
  Per rule, the order of the parameters (applies, the two value lookups, the comparison) is the
  order of the `%s` in the SQL. `test_every_operator_has_as_many_placeholders_as_parameters`
  and `test_request_text_is_only_in_the_parameters` check both. `filter_properties` builds its
  `IN` list from fixed `%s` the same way.
- **Input edge cases.** A missing or empty `props` gives no filter and no query. A text longer
  than 4000 characters, invalid JSON, deep nesting (`RecursionError`, D-4), a non-object, a
  missing `rules` and a wrong `match` are all refused as "cannot be read". A boolean
  `property_id` or option id is refused. JSON `NaN`, `Infinity` and `1e400` as numbers are
  refused by `parse_value`, as are values over the number limit. A very large `property_id` is
  "no longer in use". Duplicate option ids are refused, and an inactive option passes.
- **The order in both routes.** In both `list_equipment` and `asset_list`, `_list_filters(cur)`
  runs inside the cursor block before `accessible_unit_ids`. `get_db()` comes first, so the
  database down is 503 (`test_database_down_is_503`). CR1-01 asks for the missing asset-list
  test.
- **The matching rules.** *Applies* is the class link or `all_classes`, and Location adds
  `e.level = GEO_LEVEL`. The value in force is `COALESCE(own, model)`. `ne` and `not_in`
  leave out a node with no value (D4). All rules join with AND and Any rules with OR, in
  brackets, and the result joins the other filters with AND. The API tests cover each rule of
  brief § 8.2, including a hidden own value, a part without a model, every-class and Location.
- **Permissions.** No new key. Both routes keep `equipment:read` and the unit scoping. The
  dialog's reads are `masters:read`. No actor comes from the client.
- **Shared fixtures (BR1-06, BR2-01, BS1-02).** `make_property(admin, uniq)`, `link` and
  `every_class` are in `conftest.py`, and the names come from `Uniq.property_name`.
  `every_class` turns `all_classes` off after its test, as admin. pytest resolves the
  `make_property` that `every_class` asks for in the test's own module, so
  `test_properties_api.py` keeps its own `make_property` signature (D-11). The `_numbers`
  counter is gone. No S062 browser test makes an every-class property.
- **The pure core and the thin shell.** Every rule and the SQL text are in
  `property_filter_core.py`, which imports no Flask and no database. `_property_filter` only
  reads, calls the core and raises `ApiError`. The frontend helpers are presentational. The
  cross-reference comments of BR1-11 and BS1-06 are on `linked_properties`, `on_level`,
  `lock_value_properties` and `_applies`.
- **Reuse.** The value messages are `properties_core`'s constants, and the number check is
  `parse_value`. LIKE escaping uses `api_common.like_pattern`. `filtersLabel` uses
  `describeFilter`, so the print header and the list use the same words.
- **The dialog (§ 5.3).** It is in `FormModal` (`modal-dialog-scrollable`, footer fixed). It has
  `saving` against a second tap and `dirty` for the discard guard. *Match* is shown from two
  lines, above them. There are at most 10 lines, with the text "10 conditions at most". A
  refusal shows under its line with `revealError`, and any other failure at the top. A class
  filter narrows the property list to the class's active properties, and a bookmarked line's
  property is listed last. A new property resets the operator and clears the value. The note
  under `ne` and `not_in` lines is wired.
- **The list screen.** An unreadable `props` sends no list request and shows one message,
  without *Retry*. *Clear property filter* removes the key. The first filter widens the level
  only when the URL has no `level` and no `props` (`propsChanges`). `listUrl`, `filterKey` and
  `hasFilters` include `props`. The print page loads the properties only when the query has
  `props`.
- **Browser tests.** Each *Automated* check of § 8.4 has a test that asserts what the user
  sees: the rows, the filter line's text, the URL, the level select, the message under its line.
  Every flow test opens its dialog through `openPropertyFilter`, which calls `expectDialogFits`.
  The one `@device` test is a fit check by its title and purpose. The other tests are
  untagged, as they should be.
- **Manual checks.** The impl report's `## Manual checks` has both **important** checks of § 8.4
  as `[auto]`, each with its test. There is no real-device check (§ 8.5), so no row in
  `docs/steps/device-checks.md` is due. That file's diff is IDE table re-padding only.
- **The docs pass.** `docs/Plan.MD` § 4.1 has the coder's "Built" sentence after the
  orchestrator's "Decided" sentence. `.claude/CLAUDE.md` § SMTW-Review maps `equipment` and
  `asset-list` to S062. There is no migration, so the schema docs are not due.
- **Scope.** Everything in brief § 1 is built. Nothing outside it is built. D-1 to D-12 list
  every departure and choice I found in the code.
- **Scope B text.** "Filter by property", "Apply filter", "Add condition", "Remove condition",
  "Clear property filter", "Complete or remove the empty condition", "Machines with no value
  are not included." and the backend messages are short and plain. The one exception is
  CR1-02.

## Manual browser check for the user

None is needed beyond the coder's passing runs. Optional: open the dialog on a phone with a
choice property of many options. The body scrolls inside the dialog, and *Apply filter* stays in
the footer.

## Feedback

- waste: `git diff refs/steps/S061 --stat` lists S061's untracked step files and `test_migration_v34.py` as deleted, because the snapshot holds them and the working tree has them only as untracked files; I had to work out that they are not S062 changes (about 2 min).
- idea: the orchestrator's prompt could give the exact diff command that leaves S061's files out, e.g. `git diff refs/steps/S061 -- backend frontend docs/Plan.MD .claude` plus `git status --short` for the new files.
