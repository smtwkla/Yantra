Step: S061 — Properties for every class, and a GPS location
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 27-10-2026

# S061 — Code review, round 1

**Verdict: no `blocker` or `major` finding is open.** Two `minor` findings and four nits. All
three unit suites pass and the build check passes.

## Test run

- `YANTRA_TEST_RUN=s061cr1 tooling/run-tests.bat`: backend PASSED, 3169 passed; frontend PASSED,
  192 passed; tooling PASSED, 185 passed (ALL SUITES: PASSED). The run applied v34 on its fresh
  test databases.
- `npx vite build` in `frontend/`: built, with only the existing chunk-size warning.
- Browser tests: I ran none. No finding of mine needs a browser run. The coder's runs stand: the
  targeted run (`equipment.spec.js`, `masters.spec.js`, `screens.spec.js`: 77 passed, 1 skipped)
  names the right specs for the screens and APIs the step changed, and the whole-suite run once
  (229 tests, 222 passed, 7 skipped, 0 failed).
- **Not tested on MariaDB 11.8** (fact). Production runs 11.8.8; v34 ran on the dev image 11.4
  only. The coder had no go-ahead to pull a `mariadb:11.8` image, and I pulled none. The risk is
  the one the brief accepts in § 9 A1. The queued dev-image step closes it.

## Findings

### CR1-01 (minor) — a very long number in a Location gives a server error

- **Where:** `backend/properties_core.py:333` (`_parse_geo`).
- **Problem:** `Decimal(text).quantize(GEO_DECIMALS, …)` runs before the range check. The regex
  takes any count of digits. `quantize` raises `InvalidOperation` when the result needs more than
  28 digits (the default context), so a number with 23 or more digits before the point is not
  answered with a message.
- **Failure scenario:** an engineer pastes a wrong clipboard into the GPS location box, e.g.
  `"1111111111111111111111111, 5"`, and taps *Save values*. The API answers 500, and the dialog
  shows a general error instead of the latitude message under the field. I checked it with
  `parse_value("geo", …)`: both a long latitude and a long longitude raise `InvalidOperation`.
  `_parse_number` does not have this fault, because it never calls `quantize`.
- **Fix:** check the range on the unrounded `Decimal` first (it compares without the precision
  limit), then round. Or catch `InvalidOperation` and answer the range message. Add the two long
  inputs to `test_refusals` in `test_properties_core.py`, red before the fix.

### CR1-02 (minor) — *Use my current location* is a small button on a floor screen

- **Where:** `frontend/src/components/PropertyInput.vue:101`.
- **Problem:** the button has `btn-sm`. The floor checklist (brief-reviewer, *Use on the floor*)
  says not to shrink tap targets on floor screens. This button is the main action of the GPS
  check: the user taps it standing at the machine, on a phone, perhaps with gloves (device-check
  rows 41–43). The Yes / No buttons in the same component have the full size.
- **Failure scenario:** at a stockyard genset a fitter with gloves misses the small button and
  taps the input, so the phone keyboard opens over the dialog instead of the location prompt.
- **Fix:** drop `btn-sm` (keep `btn-outline-secondary mt-2`).

## Nits

- **CR1-03** (nit) `frontend/src/components/PropertyInput.vue:101-105`, `:123`: for a Location,
  the server's refusal ("The latitude must be between -90 and 90") shows under the button and the
  accuracy line, not right under the input. Put the button and its two lines after the `error`
  line for this type, so the refusal stays beside its field as the component's comment says.
- **CR1-04** (nit) `frontend/src/views/masters/PropertiesPanel.vue:283` (D-8, scope B): "Not on
  the model: each machine has its own, for example where it stands." starts with a fragment. Use
  "Each machine gets its own value, for example where it stands. Models do not hold it." The
  other two D-8 texts are fine.
- **CR1-05** (nit) `frontend/src/components/PropertyInput.vue:44-61`: while the reading runs (up to
  20 s) the button only greys out; show "Finding the location…" in it. Clear the accuracy line
  when the user then types a value, so "About 12 m accurate" does not describe a typed position.
- **CR1-06** (nit) `docs/schema.html:65`: the three changed entity blocks (`property_definitions`,
  `model_property_values`, `equipment_property_values`) carry an empty line (`\n\n`) before the
  new columns; no other block has one. Remove it, so the hand edit looks like the generated text.

## The points the orchestrator asked about

- **D-1 (the precondition passes v34's own seed row): agreed.** DDL commits on its own in
  MariaDB, and the `INSERT IGNORE` is v34's last statement. So the seed exists only when every
  `ALTER` before it ran. A hand-made row cannot carry `created_by = 'migration-v34'` (the column
  is `NOT NULL`, and `actor()` gives a login name). The brief asks both for the refusal and for a
  re-runnable migration (§ 4, § 8.3), and this reading meets both. `test_a_rerun_changes_nothing`
  covers the path (it deletes the version row and migrates again).
- **D-6 (inactive every-class properties in the class table): agreed.** The class table already
  lists inactive linked properties with "(inactive)"; one rule for both is simpler. The picker
  still leaves every-class properties out, active or not.
- **D-8 (three screen texts):** "Shows on every machine. No need to add it to each class." and the
  placeholder meet scope B. The third text is CR1-04.
- **Migration v34 against the brief § 4:** the ENUM `MODIFY` appends `geo` in the same `ALTER` as
  the two flags; each value table gets the two columns and three named CHECKs, each dropped if it
  exists first; the seed matches the brief word for word. `_PRECONDITIONS[34]` passes an absent
  table (`information_schema.TABLES`, `TABLE_SCHEMA = DATABASE()`), compares by the column's
  collation, and returns the brief's refusal text.
- **`test_migration_v34.py`:** covers every case of § 8.3: a fresh database (columns, ENUM, six
  CHECKs, seed with both flags); the empty database through the precondition; a v33 database with
  model values, item values and an event, every row kept and the new columns NULL or 0; a re-run;
  the refusal of "gps LOCATION", with nothing changed, then a pass after a rename. The CHECK test
  inserts each broken row into both tables and asserts error 4025.
- **Schema docs (gate B):** `schema.md` names v34, the `geo` type, both flags, the seed row, the two
  columns with their types and all six CHECK names. `schema.html` names v34 in its meta line and
  has the four new columns in the Equipment tab. The Mermaid overview lists keyed columns only, so
  it rightly does not change. The ENUM values are not shown in the HTML for any table, so `geo`
  is not missing there.
- **§ 5.7 locks:** no new lock and no new order. The flags are read from the property rows the
  saves lock `FOR UPDATE` at (2). `update_property` locks the property row, then reads both value
  tables `LOCK IN SHARE MODE`, so a model save and a *per_item_only* switch run one after the
  other. The two LOCK ORDER notes (`properties.py`, `item_properties.py`) each gained the line the
  brief asks for.
- **Always-check tests:** no new route and no new key, so `test_role_matrix` and the `db_down`
  fixture need no change (both in the green run). No new table, so `_TABLES` keeps its list.
  `_SEEDED_TABLES` now holds a tuple of creators and keeps `migration-v31` and `migration-v34` on
  `property_definitions`; `SEED_CREATOR` stays for `test_migration_v11.py`.

## Checked and found consistent

- Scope: everything in brief § 1 is built (the type, both flags, the seed, top-level only, the
  hint, Masters' tick boxes and badges, the class table and the picker). Nothing outside the brief
  was built. D-1 to D-10 are listed in the report and are readings of the brief, not departures.
- Rules: the flags parse as `active` does ("Choose yes or no"); the 409 for `per_item_only` names
  its field and only counts model values; turning it off is always allowed; a model save of a
  per-machine property gets 400 "Set this property on each machine, not on the model"; an item
  save of a Location on a part gets `NOT_ON_CLASS`; `_same_value` compares the location columns
  as Decimals, so a re-save writes nothing; `item_events` drops "(model)" for a per-machine
  property; `map_url` is built from the stored numbers only.
- Every caller of `linked_properties`, `lock_value_properties`, `equipment_properties` and
  `check_values` was updated; no other module reads the value tables.
- Pure core, thin shell: the parse, the level rule (`on_level`), `value_in_force` and
  `moving_hint` are pure and tested; the routes only fetch and store. The frontend's location
  helpers are display-only and unit-tested (D-7).
- Security: the keys are unchanged; no actor from the client; the new SQL uses placeholders (the
  `IN (…)` lists are built from counts, not values). The map link carries no user text.
- The database down: no new route; every route still answers 503 through `get_db()`.
- Test coverage: the core and API tests cover the § 8.1 and § 8.2 lists, failure modes included
  (bad locations, flags, 409, 400 on a model save, a part, an operator's 403). The every-class
  fixtures turn the flag off again, so later tests on the same worker database are not affected
  (D-10).
- Browser tests: each *Automated* check of § 8.4 has a test that asserts what the user sees (the
  value, the link's `href`, the history line, the message under the input, the badges, the
  picker's empty result). Each flow test calls `expectDialogFits` on the dialogs it opens. The new
  tests are untagged logic tests, which is right. The changed S043 hidden-card test uses a
  component-unit (`noModelPart`), as BR2-05 asks.
- Manual checks: the report's `## Manual checks` carries both **important** automated checks as
  `[auto]` with their tests, and both **important** real-device checks as unticked boxes; rows
  41–43 are in `docs/steps/device-checks.md` with account, network and place.
- Docs pass: `schema.md`, `schema.html`, `Plan.MD` § 4.1, `device-checks.md` and the
  `.claude/CLAUDE.md` § SMTW-Review spec-to-step map are updated and listed in `## Docs updated`.
  No secret, role or Keycloak change, so the other listed docs are not due.
- Track: full, as the step has a migration and a precondition.

## Manual browser check (for the user)

- None beyond the device checks: rows 41–43 of `docs/steps/device-checks.md` (Android in Chrome,
  iPhone in Safari and as the installed app, and the rough reading inside a shed), done by IT
  Admin on production after the deploy.

## Feedback

- hindrance: the first background run of `run-tests.bat` through `cmd //c` lost the backslashes and ran nothing ("'toolingrun-tests.bat' is not recognized"), and exited 0 (1 run lost, about 1 min).
- idea: `git diff -w` of `docs/schema.html` is one 70 KB line per changed tab; a short checker that prints each table's columns from the `TABS` JSON would make the gate-B schema check quick (2 extra greps here).
