```
Step: S062 — Filter the equipment list by property
Doc: brief-review r2
Author: Brief reviewer (Fable)
Date: 27-10-2026
```

Reviewed against: d6431f1 (no uncommitted code; S061 is approved and not coded, its rules read from `docs/steps/S061-global-properties-gps/1-brief.md`)

**Verdict: no `blocker` or `major` finding is open.** One `minor` finding (a second name counter planned beside `conftest.py`'s `Uniq`) and three nits. Every round-1 finding marked `Accepted` is in the brief's text, not only in the Review log. Facts file used: `scratch/brief-facts-S062.md`.

**Re-read in this round** (the brief is untracked, so there is no `git diff` of round 1; I used the orchestrator's list and the Review log): the header; § 1 items 2, 3, 4a; § 3 Backend, Frontend, Tests; § 5.2 (the two functions, checks 3 and 6); § 5.3 *Value input* and *Apply*; § 5.4 the cross-reference; § 7 D11, D12; § 8.1; § 8.2 fixtures line; § 8.3; § 8.4 the first two items. The other sections were not re-reviewed.

## Findings

### BR2-01 — minor — The moved fixtures bring a second name counter into `conftest.py`, beside `Uniq`

**Problem.** § 3 Tests moves `make_property`, `link` "and their name counter" from `test_item_properties_api.py:18, 58-74` to `conftest.py`. `conftest.py` already has one counter for every unique name and code: the class `Uniq` (`conftest.py:283`, the fixture `uniq`, `:336`), with `site_code()`, `class_code()`, `type_name()`, `designation()`, `username()`, and every other `make_*` fixture there takes `uniq` (`make_site(admin, uniq)`, `:373`; `make_type`, `:446`). A module-level `itertools.count` next to it is a planned duplicate of that pattern.

**Why it matters.** Two ways to make a unique name in one fixtures file; the next fixture author must choose. Small, but it is exactly what the move was meant to avoid.

**Options.**
- (a) **Recommended:** add `Uniq.property_name(prefix)` → `f"{prefix} {self._next():04d}"`, and write the moved fixture as `make_property(admin, uniq)` using it. `test_item_properties_api.py` drops its `_numbers` (used only by `make_property`, `:62`). `test_properties_api.py` keeps its own fixtures and counter as the brief says.
- (b) Move `_numbers` as planned. Works; a second counter in the shared file.

## Nits

- **BR2-02** (nit) § 1 item 4a, § 8.3: "a level the user chose, leaves the level as it is" cannot hold for a user who chose *Equipment*: `update()` drops `level=equipment` from the URL (`EquipmentView.vue:68`), so a chosen *Equipment* and the default look the same, as they do for the search (`applySearch`, `:142`). Say the rule on the URL: "when the URL has no `level`", and give the pure helper that input.
- **BR2-03** (nit) § 1 item 3, D12: with an unreadable `props` the list request still carries it (`listUrl`), the API answers 400 (check 1), and the list's error box with *Retry* shows above the new filter line. The user then reads the refusal twice, and *Retry* does nothing. Say that this is accepted (the box says what is wrong, the line holds the button), or skip the list request when `props` does not decode and show the empty list.
- **BR2-04** (nit) § 8.4 first check: `propertySetup` makes one top-level machine of a fresh class with its model's values (`frontend/e2e/support/properties.js:24-46`); it makes no part. The "motor" needs `noModelPart(parent, cls, name)` (`properties.js:53`, a component-unit with no model) and its own value by `PUT /api/equipment/<id>/properties`, or a new helper. Name the set-up, and say that the machine itself has no value of that property, so only the part matches.

## Checked and found consistent

- **Round-1 answers in the text.** BR1-01: § 1 item 4a, § 5.3 *Apply*, D11, § 8.3, § 8.4. BR1-02: § 3 Backend, § 5.2 (two functions, `property_ids`), § 8.1. BR1-03: § 1 item 3, D12, § 8.3, § 8.4. BR1-04: § 1 item 3, § 8.3 (" · ", the match said once). BR1-05: § 5.3 *Value input*. BR1-06: § 3 Tests, § 8.2. BR1-07, BR1-08: § 1 item 2. BR1-09: § 5.3 *Apply* (`saving`). BR1-10: § 5.2 checks 3 and 6. BR1-11: § 5.4 *applies*. BR1-12: § 3 Frontend. BR1-13: § 8.1.
- **§ 1 item 4a, the search's rule.** `applySearch` widens the level when the search was empty and the URL's level is the default (`EquipmentView.vue:141-142`); `update()` keeps `level=all` and drops the page (`:64-68`). Plan.MD § 4.1 lists motor and gearbox as components (`Plan.MD:196`). A `props` change changes `filterKey` (`:198`), so the ticks clear as the brief says.
- **§ 5.2 the two functions.** `parse_property_ids` refuses a boolean (`properties_core.py:333-334`), the guard the brief cites. The number messages exist as constants: `ENTER_NUMBER`, `TOO_MANY_DECIMALS`, `NUMBER_TOO_BIG` ("Enter a smaller number", `:45-47`), `TEXT_TOO_LONG`, `ENTER_TEXT`, `CHOOSE_YES_NO`, `CHOOSE_OPTION` (`:48-51`). `parse_value` answers `(None, None)` for a blank (`:278`), so the brief's own "a blank number: Enter a number" rule in the core is needed and stated.
- **§ 3 Tests, the override.** `test_properties_api.py` defines `make_property(engineer)` and `link(engineer)` (`:38`, `:51`) with other signatures; a fixture defined in a test module overrides a `conftest.py` fixture of the same name, so that module needs no change. `_numbers` in `test_item_properties_api.py` is used by `make_property` only (`:18`, `:62`). `admin` is a `conftest.py` fixture (`:355`). No other test module defines `make_property` or `link` (facts file; grep of `def link(`).
- **§ 3 Frontend, the print page.** `AssetListPrintView.vue` loads classes and types with the list today (`:39`); `ensureProperties` (`stores/masters.js:84`) fetches `/api/masters/properties?include_inactive=1`, so a conditional call adds a request only with `props`. `filtersLabel(params, lookups)` already takes a `lookups` object (`assetList.js:45`); `props` as a string passes `FILTER_KEYS`'s `text()` test (`:9-11`).
- **§ 5.4 against S061 § 5.3.** S061 shows a property when it is active and linked to the class or `all_classes`, and a `geo` property only at level `equipment` (S061 brief `:265-267`): the *applies* SQL says the same. A per-machine property (S061 § 5.4) changes which dialog sets the value, not which node shows it, and S061 keeps "own wins, else the model's" (`:304-305`), so the COALESCE needs no per-machine case.
- **Header file count.** § 3 names 3 backend, 5 frontend, 9 test and 2 doc files: 19.
- **§ 8.5.** Still none, with its reason; the round-1 changes added no check a browser cannot judge.

## Feedback

- hindrance: the brief is untracked, so `git diff` could not show round 1's changes; I worked from the orchestrator's section list and the Review log (the rule asks for a diff). Idea: the orchestrator copies the brief to `scratch/S0NN-brief-r<N>.md` before answering a round, so the next round can diff.
- waste: `scratch/brief-facts-S062.md:145-157` again lists `PropertyFilterModal.open` and `_` as code names with 64 and 26 files (the round-1 idea stands).
