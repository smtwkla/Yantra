```
Step: S062 — Filter the equipment list by property
Doc: code-review r2
Author: Code reviewer (Opus)
Date: 27-10-2026
```

# S062 — Code review, round 2 (verify)

**Verdict: no blocker or major finding is open.** All six findings of round 1 are fixed. The
CR1-04 fix brings in one new minor fault: the dialog can ask "Discard your changes?" when
nothing changed (CR2-01). D-1 (`router.push`) stays with the user; I did not reopen it.

Re-read: the parts of the five files the fix round lists. These are `_option_ids` in
`backend/property_filter_core.py`, `filter_properties` in `backend/properties.py`, `TestAssetList`
in `backend/tests/test_property_filter_api.py`, the script and the yes/no select of
`frontend/src/views/equipment/PropertyFilterModal.vue`, and the filter row and `load()` of
`frontend/src/views/EquipmentView.vue`. I also read `ensure()` in `frontend/src/stores/masters.js`
and the `dirty` gate of `FormModal.vue`, because the CR1-04 fix depends on them. The working tree
matches snapshot `refs/steps/S062` (12d87c9) for every tracked file.

## Tests

- **Unit suites** (`YANTRA_TEST_RUN=s062cr2 tooling/run-tests.bat`): backend PASSED, 3262
  passed (132 s); frontend PASSED, 231 passed (27 s); tooling PASSED, 185 passed.
- **Build check** (`npx vite build`): built, with only the existing chunk-size warning.
- **Browser tests:** I did not re-run them, because no finding of mine needs a run. The coder's
  targeted run covers the right specs for the fix round: `equipment.spec.js`,
  `asset-list.spec.js` and `screens.spec.js` at Normal, with 65 passed and 1 skipped (an existing
  skip). The fix round changed the dialog and the equipment list only.

## Round 1 findings

| ID | Severity | Status | Checked |
|---|---|---|---|
| CR1-01 | minor | Fixed | `TestAssetList.test_a_user_with_no_units_gets_400_for_a_bad_filter` sends `props={broken` as a user with no units to `ASSET_LIST` and asserts 400 `{"error": UNREADABLE, "field": "props"}`. If `_list_filters` moved below the unit check, the route would answer 200, and the test would fail. The fix round gives no red run, but it states the reason: the test guards correct code as built. That is acceptable. |
| CR1-02 | minor | Fixed | The yes/no value select's first option reads "Choose Yes or No" (`PropertyFilterModal.vue:308`). This matches `properties_core.CHOOSE_YES_NO`. |
| CR1-03 | nit | Fixed | The *Clear property filter* button is `btn btn-sm btn-outline-secondary` with no `py-0`. |
| CR1-04 | nit | Fixed, with a new fault | `open()` now calls `modal.value.open()` before `loadChoices`, and a read error still shows at the top of the dialog. See CR2-01. |
| CR1-05 | nit | Fixed | The comment on `_option_ids` says why `any()` keeps unhashable values away from `i not in known`. `len(set(raw))` runs only after `any()` is false, so every id is a whole number by then. |
| CR1-06 | nit | Fixed | The first string of the `cur.execute` call in `filter_properties` has no `f` prefix. |

## Findings

### CR2-01 (minor) — the dialog can ask "Discard your changes?" when nothing changed

`frontend/src/views/equipment/PropertyFilterModal.vue:139` (`initial = snapshot()` in `open()`),
with `ruleOf` at lines 59-68.

- **Problem.** `open()` now takes the `initial` snapshot before the property read finishes.
  `snapshot()` builds each rule with `ruleOf`, and `ruleOf` needs the line's data type from
  `properties`. Before the read finishes, the data type is `undefined`. A yes/no line then gives
  `value: "true"` (a string), and a choice line gives `value: ""`. After the read, the same lines
  give `true` (a boolean) and the option-id list. So `dirty` turns true with no change by the
  user, and `FormModal` stops Esc, ✕ and Cancel with "Discard your changes?". Before the fix
  round, `open()` waited for the read, so this could not happen.
- **Failure scenario.** A technician opens a bookmarked list on a slow mobile network. The URL
  has `props` with a yes/no line, such as "Has guard is Yes". `load()` asks for the properties,
  but the answer has not come yet. The technician taps *Properties (1)*. The dialog opens at
  once, and the property list fills in a moment later. The technician changes nothing and taps
  Cancel. The dialog asks to discard changes they never made. The same happens on each open
  after the page's own property read failed, because `properties` stays `null` until the
  dialog's read succeeds.
- **Fix.** Keep the dialog opening at once, but compare like with like. In `open()`, store a
  copy of the starting `match` and lines (for example `initialLines` and `initialMatch`). Let
  `dirty` build both sides with `ruleOf` at the time it is read. Then both sides use the same
  data types, before and after the read. The other way is to take `initial = snapshot()` after
  `loadChoices`, but then a change made during the read would count as the start.

## Nits

None.

## Checked and found consistent

- **The CR1-04 fix, apart from CR2-01.** The dialog shows its lines at once. A bookmarked line's
  property shows in its select when the list arrives, because `lineChoices` reads `properties`
  through `computed`. `chooseProperty` runs only on the select's `change` event. So the late
  property list does not reset a bookmarked operator or value. *Apply filter* stays disabled
  until the data types are known, because `ruleComplete` gets an `undefined` data type until
  then. A failed read shows its message in the dialog's top error, as before.
- **The asset-list test (CR1-01).** It needs no property fixture, because the filter text cannot
  be parsed. It pins both the status and the body, so a 400 for another reason would fail too.
- **The other three changed files.** The comment (CR1-05), the `f` prefix (CR1-06) and the
  button class (CR1-03) change no behaviour.
- **Docs.** The fix round says "Docs updated: none". That is right: no rule, API, secret or
  schema changed.
- **Manual checks.** No change since round 1.

## Manual browser check for the user

None. CR2-01 shows only on a slow network, and a unit or browser test can pin it after the fix.

## Feedback

- none
