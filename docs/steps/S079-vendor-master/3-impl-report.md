```
Step: S079 — Vendor master
Doc: impl-report
Author: Coder (Opus)
Date: 30-10-2026
```

# S079 — Vendor master: implementation report

The step is built as the brief says, with one change the orchestrator asked for: the phone rule is
a factory, `phone_parser(label)`, so S080 can reuse it for the call-out number. Unit suites, the build,
the targeted browser specs and the schema docs check are green. The whole browser suite at Normal
has 3 failures outside this step: two from the empty v0.1.14 change-log section (already at HEAD)
and one lane-order dependence in an S068 test (§ 6).

## 1. What was built

- **A vendor master.** Migration v42 adds the table `vendors` (name, phone, note, active, who and
  when; shared by all sites). It also adds `people.vendor_id` with a foreign key, an index and the
  CHECK `chk_people_vendor`: only a contractor may have a vendor. No seed rows and no links.
- **Masters › Vendors**, a new tab after *Trades* and before *Team*. It shows Name (with the phone
  and the note under it), People (the active Team records linked to the vendor, or "None"), Status
  and *Edit*. It has *Show inactive*, *Add vendor* and one dialog with *Deactivate* / *Reactivate*.
- **A vendor on a contractor's Team record.** The Team dialog has *Vendor (optional)*, shown only
  while *Contractor* is chosen. The Team list shows "Contractor · Atlas Copco", with " (inactive)"
  for a deactivated vendor.
- **A warning before a stored link changes**, on *Edit person*: to another vendor, or to none.
- **The rules in the API and the database**: a direct employee with a vendor is refused (400); a
  new link needs an existing, active vendor (400); a vendor is never deleted; deactivating one is
  always allowed, and its links stay.

## 2. How it works

### Backend

- **`masters_core.py`** (pure):
  - `phone_parser(label)` returns a parser for an optional phone field. It clears on `null` or
    an empty string, trims and collapses inner spaces, allows at most 20 characters, and checks
    the pattern `^\+?[0-9 ().-]*$` with 6 to 15 digits. The messages name the field by `label`;
    the rule text is the brief's. `_parse_phone = phone_parser("Phone")`.
  - `validate_vendor(data, creating)` validates `_VENDOR_FIELDS`. The name uses
    `_parse_manufacturer_name` (the same rule as a manufacturer). The note uses
    `optional_text_parser("Note", 255)`.
  - `_PERSON_FIELDS` gains `vendor_id` through `_parse_optional_id("Vendor")`.
  - `vendor_link_error(employment, vendor_id, vendor_sent)` returns `(field, message)` or `None`.
    The field is `vendor_id` when the body sent a non-null vendor, else `employment`.
- **`masters.py`** (shell):
  - `GET /api/masters/vendors` reads `_VENDOR_SELECT`, which counts `people_count` in a subquery.
    `_vendor_out` drops `phone` for a reader without `equipment:edit`.
  - `POST` inserts with no transaction (as manufacturers). `PUT` locks the vendor row, then
    updates it. Neither counts or locks a person.
  - `UNIQUE_KEY_ERRORS["uq_vendors_name"]` gives the 409 text of § 5.1.
  - The people routes read `_PERSON_SELECT` (people joined to vendors for `vendor_name` and
    `vendor_active`). `_people_out` turns `vendor_active` into a boolean, or `None` with no
    vendor. `list_people` filters on `p.active` and orders by `p.name, p.id`.
  - `_check_vendor_link(cur, employment, stored_vendor_id, clean)` runs rule 1 on the effective
    values, then calls `_check_new_vendor` when the body sends a non-null vendor that differs
    from the stored one. `_check_new_vendor` reads the vendor `LOCK IN SHARE MODE` and refuses
    a missing or inactive one with the trade's wording.
  - `create_person` calls it first in the transaction, before the trades. `update_person` calls
    it after the person lock and the 403s, before the trades (BR1-03). A refusal raises inside
    `transaction()`, so nothing of the save is kept.
  - The module docstring and the Team block's comment state the lock order person → vendor →
    trades.

### Frontend

- **`stores/masters.js`**: `vendors`, `ensureVendors`, cleared by `resetMasters`.
- **`VendorsPanel.vue`**: the manufacturers panel's pattern (`FormModal`, `useMasterForm`,
  `ActiveToggle`). `toBody` sends an empty phone or note as `null`. The panel loads with
  `ensureVendors({ refresh: true })`, so People is fresh each time the tab opens.
- **`PeoplePanel.vue`**:
  - `vendor_id` in `blank` and `fromRecord`;
  - `toBody` always sends `vendor_id`: the number while *Contractor* and a vendor are chosen,
    else `null`;
  - a `watch` on the employment clears the vendor when *Direct employee* is chosen;
  - `vendorChoices`: the active vendors, then the person's stored vendor as "<name> (inactive)"
    when it is inactive;
  - `vendorChangeLine`: the warning texts of § 5.5;
  - the list's suffix " · <vendor>" and " (inactive)";
  - `reload` adds `ensureVendors(refresh)`.

## 3. Files touched

| File | Change |
|---|---|
| `backend/local_db.py` | Migration v42 with its comment (no precondition, why, the rollback) |
| `backend/masters_core.py` | Phone constants, `phone_parser`, `_parse_phone`, `_VENDOR_FIELDS`, `validate_vendor`, `vendor_id` in `_PERSON_FIELDS`, `DIRECT_WITH_VENDOR`, `vendor_link_error` |
| `backend/masters.py` | Vendor routes, `_VENDOR_SELECT`, `_PERSON_SELECT`, `_vendor_out`, `_fetch_vendor`, `_check_vendor_link`, `_check_new_vendor`, the 409 entry, the people routes, the lock notes |
| `backend/tests/test_migration_v42.py` | New: § 8.1 |
| `backend/tests/test_vendors_api.py` | New: § 8.2, the vendor routes |
| `backend/tests/test_people_api.py` | `TestVendorLink` |
| `backend/tests/test_masters_core.py` | `TestVendor`, `TestVendorLink` |
| `backend/tests/conftest.py` | `"vendors"` after `"people"` in `_TABLES`, `Uniq.vendor_name()`, fixture `make_vendor` |
| `frontend/src/stores/masters.js` | `vendors`, `ensureVendors`, reset |
| `frontend/src/views/masters/VendorsPanel.vue` | New: the Vendors tab |
| `frontend/src/views/MastersView.vue` | The *Vendors* section after *Trades* |
| `frontend/src/views/masters/PeoplePanel.vue` | The vendor select, the clearing, the warning, the list suffix |
| `frontend/tests/masters.test.js` | `ensureVendors` in the path case and in the reset case |
| `frontend/e2e/masters.spec.js` | The section-loop entry and four S079 tests |
| `docs/schema/notes.json`, `schema.json`, `schema-data.js` | `vendors`, `people.vendor_id`, the area note (the last two generated) |
| `docs/Plant-Facts.md` | § 4 the five vendors; § 10 a change-log line |
| `.claude/CLAUDE.md` | § SMTW-Review: *Vendor link (S079)* |
| `docs/steps/S079-vendor-master/1-brief.md` | Status |

## 4. Decisions taken

- **`phone_parser(label)`, a factory** (decision taken at the orchestrator's request, from S080's
  brief review BR1-04). The vendor phone uses `_parse_phone = phone_parser("Phone")`. S080 calls
  `phone_parser("Call-out number")`. The pattern, the bounds and the rule text are as the brief
  says. A unit test checks that the messages name the field.
- **`_check_vendor_link` beside `_check_new_vendor`.** The brief names "the link check and
  `_check_new_vendor`" in both person routes. I put both in one helper,
  `_check_vendor_link`, so the two routes call one line each. `_check_new_vendor` keeps the
  brief's name and holds the share-locked read.
- **`POST /people` runs rule 1 inside the transaction**, right before the vendor read, as § 5.3
  lists it. It is pure, so where it runs changes nothing.
- **`DIRECT_WITH_VENDOR` and `PHONE_RULE` are constants** in `masters_core.py`, so the tests and
  S080 use the same text.
- **The vendor routes' place**: a new section after the manufacturers-and-models block, before
  the failure codes (the brief says "after the manufacturers block"; models are part of it).
- **`create_vendor` returns the row through `_fetch_vendor`**, so the answer has `people_count`
  (0) as the list does (§ 6: "the row as in the list").
- **The Vendors tab's footnote** shows only when the table has rows; the empty state has its own
  text.
- **The Team list's vendor** is a plain-text span after the badge (class `person-vendor`), so the
  cell's text reads "Contractor · Atlas Copco".
- **The Team dialog's save label** is *Save*, as today; the brief's "*Save person* saves" names
  the action, not a new label.
- **`test_each_put_shape`** has eight cases: § 5.2's last row ("`{active: 0}`, `{name: …}` or
  `{trade_ids: …}`") is split into three.
- **`TestPermissions::test_editors_write`** is a separate test from
  `test_only_equipment_edit_holders_write` (engineer and manager → 201), so each parametrized
  case checks one thing.
- **One e2e helper, `postAsAdmin`**, local to `masters.spec.js`, makes the vendors and contractors
  by API. The support files are shared code (settings: *Shared code*), so I did not add to them.

## 5. Not done, deferred or assumed

- Nothing of the brief is left out.
- **Assumption:** `has_perm("equipment:edit")` answers for the key held at any site. The test
  `TestPhoneReaders` shows it: the engineer and the manager see the phone.
- **Not changed:** `docs/Plan.MD` (the step does not depart from it; § 3 Docs). The orchestrator's
  uncommitted edits in Plan.MD, `docs/roadmap/` and the S080 / S081 folders are untouched.
- `docs/steps/INDEX.md` already showed S079 as *Implementing*; I changed only S079's row at
  hand-over.

## 6. Tests

- **Unit suites** (`YANTRA_TEST_RUN=s079c1 tooling\run-tests.bat`, once at the end): ALL SUITES
  PASSED — backend 4170 passed (180 s), frontend 377 passed, tooling 231 passed.
- **Targeted backend runs while coding**: `test_migration_v42.py` (7), `test_masters_core.py`
  (411), `test_vendors_api.py` + `test_people_api.py` (120), `test_site_roles_api.py`,
  `test_models_api.py`, `test_masters_api.py`, `test_rbac.py` (288): all passed.
- **Build**: `npx vite build` green (only the existing chunk-size warning).
- **Schema docs**: `tooling\schema-docs.bat write`, then `check` with `YANTRA_TEST_RUN=s079c1`:
  PASSED, exit 0 (migration v42).
- **Browser, a new test alone**: `E2E_LANES=1`, `e2e/masters.spec.js --project=phone-chromium -g
  S079`: 4 passed, first run.
- **Browser, targeted** (Normal): `e2e/masters.spec.js e2e/floor.spec.js e2e/tickets-raise.spec.js
  e2e/screens.spec.js` (the brief's § 8.4 list: the changed screen, the specs that open the Team
  dialog, and screens): 72 passed, 2 skipped (existing skips), 93 s.
- **Browser, whole suite** (Normal, once at the end, `tooling\run-e2e-tests.bat`): 317 passed,
  15 skipped, **3 failed**, 174 s. None of the three is in a spec or screen this step changed:
  - `changelog.spec.js:14` (S048, `it_admin` and `admin`, desktop only): **a fault already at HEAD.**
    Release v0.1.14 (`e77d635`) wrote an empty `## 0.1.14` section into `CHANGELOG.md`, so the
    dialog shows "No notes were written for this version." beside the badge "This version", and
    `getByText("This version")` matches two elements (strict mode). It fails again when run alone.
    S079 touches neither `CHANGELOG.md`, `VERSION`, the sidebar nor the dialog. Not fixed: out of
    scope. Fix options for the orchestrator: `{ exact: true }` in the test, or notes in the section.
  - `improvements.spec.js:97` (S068, "Closed is empty"): **passes when run alone** (the re-run of
    `changelog.spec.js improvements.spec.js`: 26 passed, the two S048 cases failed as above). In
    the whole run it shares its lane's database with a test that closes an improvement, so the
    *Closed* list is not empty. The test depends on the lane plan; S079's four new tests in
    `masters.spec.js` change the timings and so the grouping. Not fixed: out of scope.
  - The re-run was the reason stated for a second browser run: to tell an S079 fault from these.

## 7. Manual checks

- [auto] **important** engineer adds a vendor with a phone and a note; the list shows them and People None; the same name in another case is refused beside Name — `frontend/e2e/masters.spec.js::S079: engineer adds a vendor with a phone and a note; the list shows them and People None; the same name in another case is refused beside Name`
- [auto] **important** engineer links a contractor to a vendor in Team; the list shows Contractor · the vendor, and Vendors counts 1 person — `frontend/e2e/masters.spec.js::S079: engineer links a contractor to a vendor in Team; the list shows Contractor · the vendor, and Vendors counts 1 person`
- [auto] **important** changing a linked person's vendor warns; Direct employee hides and clears the vendor and the save unlinks — `frontend/e2e/masters.spec.js::S079: changing a linked person's vendor warns; Direct employee hides and clears the vendor and the save unlinks`
- [auto] a deactivated vendor is not offered for a new link; a person linked to it keeps it as (inactive) — `frontend/e2e/masters.spec.js::S079: a deactivated vendor is not offered for a new link; a person linked to it keeps it as (inactive)`
- [auto] the Vendors section opens, and an empty vendor is refused beside its field — `frontend/e2e/masters.spec.js::engineer: the Vendors section opens, and an empty add vendor is refused beside its field`
- On a real device: none (brief § 8.5). No row added to `docs/steps/device-checks.md`.

## Docs updated

- `docs/schema/notes.json`: a `vendors` line (area *Team and access*); the `people` line names
  `vendor_id` and `chk_people_vendor`; the area note adds "vendors".
- `docs/schema/schema.json`, `docs/schema/schema-data.js`: generated by `tooling\schema-docs.bat
  write` (migration 42: `vendors`, `people.vendor_id`, `fk_people_vendor`, `ix_people_vendor`,
  `chk_people_vendor`); `git diff` read.
- `docs/Plant-Facts.md`: § 4 a row with the five vendors and what each maintains (no number, no
  address); § 10 a change-log line.
- `.claude/CLAUDE.md`: § SMTW-Review, the point *Vendor link (S079)* (§ 9 Q3).
- `docs/Plan.MD`: none, because the step does not depart from § 2 item 9 and § 3's Team paragraph.
- `backend/example_secrets_app.py`, `docs/Keycloak.md`, `docs/steps/device-checks.md`: none,
  because no secret, role or real-device check changed.

## Feedback

- hindrance: the whole-suite run failed on two tests no step touched (`changelog.spec.js:14`,
  broken by the release's empty change-log section; `improvements.spec.js:97`, lane-order
  dependent), so a second browser run was needed to tell them from an S079 fault
  (`scratch/s079-e2e-normal.log`, 1 extra run, about 2 min).
- idea: a release that writes an empty change-log section could be followed by the S048 test in
  pre-flight; a test that expects an empty list (S068 "Closed is empty") could make its own unit
  instead of relying on the lane's database.

## Code review r1: CR1-01 and CR1-02, fixed by the orchestrator

- **CR1-01 (nit) — Fixed.** `frontend/src/views/masters/VendorsPanel.vue`: when vendors exist but none is active and *Show inactive* is off, the tab now says "No active vendors. Turn on *Show inactive* to see the others." instead of "No vendors yet".
- **CR1-02 (nit) — Fixed.** `frontend/src/views/masters/PeoplePanel.vue`: the Team dialog's hint checks for an active vendor and reads "No active vendors; add one under Vendors."
- Checked: `tooling\run-frontend-tests.bat` 377 passed; `npx vite build` green. No browser test asserts either text (`git grep "No vendors yet" frontend/e2e frontend/tests` finds none), so no browser run was needed.
