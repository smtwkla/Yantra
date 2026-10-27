Step: S061 — Properties for every class, and a GPS location
Doc: brief-review r2
Author: Brief reviewer (Fable)
Date: 27-10-2026

Reviewed against: d6431f1 (no uncommitted step code; only `docs/steps/INDEX.md` is modified)

# S061 — Brief review, round 2

**Verdict: no `blocker` or `major` finding is open.** Every round-1 finding marked `Accepted` is
carried into the brief's text, and each claim the new text makes about the code holds. Five
nits remain, all wording or a name; none needs a decision from the user. Facts file used:
`scratch/brief-facts-S061.md` (refreshed on the revised draft).

**Sections re-read** (the ones the Review log's answers changed, and the code they now rely on):
header; § 1 item 1; § 2; § 3 (Backend, Frontend, Tests); § 4 (statements 1–2, the precondition,
the rollback); § 5.1; § 5.2; § 5.3; § 5.4; § 7 D1, D3, D4; § 8.2; § 8.3; § 8.4; § 8.5; the Review
log. The brief is untracked, so there was no `git diff`; I compared the sections against my
round-1 file. Sections not named above were not re-reviewed.

## Findings

None of `blocker`, `major` or `minor` severity.

## Nits

- **BR2-01** (nit) § 3 Backend and § 5.3: the class table's query lives in `_class_properties`
  (`properties.py:211`), which `list_class_properties`, `add_class_properties` and
  `remove_class_property` all answer with. Name `_class_properties` as the place of the union, so
  the every-class rows also come back in the answer of *Add properties* and *Remove* (the table
  re-renders from it), not only on the GET.
- **BR2-02** (nit) § 8.2, the convention: "E2E tests assert `dt` lists with 'GPS location' as the
  last row" — the `dd` lists at the same lines (`equipment.spec.js:373`, `387`, `395`, `411`,
  `masters.spec.js:389`) gain "—" as the last entry too. Say "`dt` and `dd` lists".
- **BR2-03** (nit) § 8.2, the convention: "The rows' new keys are compared where the test is
  about them" leaves `test_equipment_api.py:1552` open, which compares whole dicts. Say which:
  a whole-row compare adds `data_type`, `per_item_only` and `map_url` to its expected rows; a
  test about ids or counts does not.
- **BR2-04** (nit) § 4, the precondition: the sentence "Without the refusal, `INSERT IGNORE`
  would keep a hand-made row …" (line 189–190) sits inside the "An absent table passes" bullet
  with a broken indent. It is the reason for the precondition itself; move it to the paragraph
  above the bullets.
- **BR2-05** (nit) § 8.4, the hidden-card test: "moves to a component of a class with no links".
  The helper the neighbouring test uses, `noModelPart` (`e2e/support/properties.js:53`), makes a
  `component_unit`. § 1 item 5 keeps component-units and components apart; say "a
  component-unit (`noModelPart`)" so the coder reuses the helper.

## Checked and found consistent

- **BR1-01** → § 4: `init_db` checks every pending version's precondition before applying any
  (`local_db.py:1206-1211`); `_v20_shape_check` and `_v25_shape_check` read
  `information_schema.TABLES` with `TABLE_SCHEMA = DATABASE()` and pass on an absent table
  (`local_db.py:1044-1057`, `1081-1084`). The v34 check as described follows them. § 8.3 has the
  migrate-from-empty case. The name compare "by the column's collation" holds: `name` is
  `VARCHAR(80)` in a `utf8mb4` table with `uq_property_definitions_name UNIQUE (name)`
  (`local_db.py:866`, `875`), so both the `WHERE name = 'GPS location'` of the check and the
  `INSERT IGNORE` of the seed compare without regard to case.
- **BR1-02** → § 8.2: the table matches my round-1 table line for line; the convention (backend
  `_made(rows)` per module, e2e lists with "GPS location" last, `masters.spec.js:360` and `:374`)
  is stated. The by-name claim holds: every property the cited tests make is named `E2E …`
  (`equipment.spec.js:366`, `381`, `407`, `445`, `468`, `489`, `531`; `masters.spec.js:332-333`),
  and "E" sorts before "G" under the table's case-insensitive collation. `conftest.py`'s
  `_SEEDED_TABLES` change is in § 3 and § 8.2.
- **BR1-03** → § 4 and D1: `chk_<table>_geo_range` is in the same re-runnable `ALTER`, with the
  reason (the columns hold 99.999999 / 999.999999); D1 now says the database checks range and
  pairing, which is true; § 8.3 checks a 91 refused. Six CHECKs: `one_value`, `geo_pair`,
  `geo_range`, on two tables.
- **BR1-04** → § 4 Rollback: states the invisible row, the `VALUE_COLUMNS["geo"]` failure after
  a link in the old release, the one-*Remove* fix and the accepted risk. Matches the old code
  (`linked_properties` joins `class_properties` only, `properties.py:272`).
- **BR1-05** → § 5.2: `(lat, lng)` Decimals, `GEO_COLUMNS` beside `VALUE_COLUMNS`, the six
  readers (`check_values`, `stored_value`, `value_display`, `_same_value`, `write_values`,
  `_VALUE_COLUMNS`), and `_same_value`'s Decimal compare, which today loops `VALUE_COLUMNS` only
  and compares `value_number` as `Decimal(str(old)) != new` (`properties_core.py:433-445`).
  § 8.2 has the re-save test.
- **BR1-06** → § 5.4, § 3 and § 8.4: the rule (model line and *Edit model values* only when a row
  is not `per_item_only`) replaces today's `node.model_id !== null` on both
  (`EquipmentDetailView.vue:304`, `319`); one computed. The e2e assertion is in § 8.4, and
  `propertySetup(tag)` with no properties makes exactly that machine (a top-level node with a
  model, `support/properties.js:24-35`).
- **BR1-07** → D3 and § 5.1: the blocked message no longer says "site"; the 409 carries field
  `per_item_only`. The shape fits the code: `property_changes` already returns
  `(field, message, 409)` for the fixed type and unit (`properties_core.py:208`, `210`), and
  `_refuse` raises `ApiError(message, status, field)` (`properties.py:110`); `useFormModal`
  shows a refusal beside its field whatever the status (`useFormModal.js:51`, `86`).
- **BR1-08** → § 5.3 and § 8.2: one row per property, *Every class* with no *Remove* linked or
  not, the link still accepted by `add_class_properties`; the once-listed test is in § 8.2.
- **BR1-09** → § 8.5: where, account (`equipment:edit` at the machine's site; `it_admin` alone
  grants nothing), network, and the iOS PWA prompt note.
- **BR1-10** → § 2: no number left "to verify"; ISO 27001 A.5.34 kept; ISO 55001 § 7.5
  (information requirements) added, and that is the clause's title in ISO 55001:2014.
- **BR1-11…BR1-16**: § 1 item 1 says the display drops trailing zeros (11); § 8.4 moves the
  hidden-card test to a part, with the reason (12); § 3 Tests has `frontend/e2e/…` (13); D3 names
  `window.isSecureContext && navigator.geolocation` and § 8.4 the two Playwright calls before
  `asPerson` (14); § 5.3 states the component-only model gap as accepted (15); § 4 item 1 puts
  the ENUM `MODIFY` in the same `ALTER` (16). MariaDB accepts a `MODIFY` beside
  `ADD COLUMN IF NOT EXISTS` in one statement, and a `MODIFY` to the same ENUM is a no-op, so the
  statement stays re-runnable (fact; the brief's dev verification line lists the other three
  clause kinds only).
- § 3 Backend: `equipment_properties` is called at `equipment.py:312`, the only caller; `node`
  there is the full row, so its level is at hand.
- § 5.1 and § 5.7: `update_property` reads both value tables `LOCK IN SHARE MODE` under the
  property's `FOR UPDATE` lock (`properties.py:150-156`); counting the model rows alone is the
  one-line split the brief describes.
- § 5.3 Saves: `lock_value_properties` selects the property row `FOR UPDATE` at step (2)
  (`properties.py:381-383`); the two flags join that select.
- § 8.4, the hidden-card test: a `component_unit` of a class with no links shows no property
  (the `geo` seed is left out by level, no other every-class property exists), so
  `node.properties.length` is 0 and the card is hidden (`EquipmentDetailView.vue:296`).
- § 8.4, the refused-permission test: Playwright denies a permission that was not granted, so
  `getCurrentPosition` gets `PERMISSION_DENIED` and the blocked message shows; no extra set-up.
- Scope A and B: the changed text keeps one term per thing; the new UI texts (the blocked
  message, the 409 message, the hint) say what happened and what to do, one line each.

## Feedback

- waste: the brief is untracked, so "diff the brief against the last round" meant re-reading
  the named sections against my r1 file by hand (about 10 minutes); a `git stash`-free way to
  snapshot the draft at each round (e.g. the orchestrator copying `1-brief.md` to
  `scratch/brief-S0NN-rN.md` before answering) would give a real diff.
