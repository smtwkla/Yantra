```
Step: S087 — Contracts across sites
Doc: impl-report
Author: Coder (Opus)
Date: 31-10-2026
```

# S087 — Implementation report

A contract no longer has a site. Its sites are now its machines' sites, worked out on every read. The four
contract keys are company-wide. Migration v50 replaces v42–v47 and drops `contracts.site_id`. Unit suites:
all green (`YANTRA_TEST_RUN=s087c1 tooling\run-tests.bat`: backend 4467 passed, frontend 409 passed, tooling 231 passed), and `npx vite build` built. Schema docs check: exit 0. Browser runs: the targeted run was green; the Normal run passed 370 tests and skipped 15, and its only failures are the two known `changelog.spec.js:14` tests, outside the step.

## 1. What was built

- **Migration v50** (§ 4.1). It replaces v42–v47 with one entry that holds the final R02 schema. `contracts`
  has no `site_id`, `fk_contracts_site` or `ix_contracts_site`; it has `ix_contracts_active_to (active,
  to_date)`. A dev or test database at any of v42–v47 converges to the same schema through seven idempotent
  `ALTER TABLE contracts` statements. The old texts are frozen in `backend/tests/fixtures/migrations_v47.py`.
  There is no `_PRECONDITIONS` entry.
- **The keys are company-wide** (§ 5.1). `contract:read_basic`, `contract:read`, `contract:read_senior` and
  `contract:edit` have left `SITE_SCOPED`. Every contract check now uses `has_perm` or `check_perm`, and a
  refusal gives the 403 text `FORBIDDEN_TEXT`. `auth_utils.sites_holding` is removed.
- **A contract's sites** (§ 5.2). `contracts_core.LINE_SITE_JOINS` and `LINE_SITES_SQL` are the one copy of
  the path from a line to its site. Every contract answer carries `site_codes`: a sorted list, or `[]` when
  the contract has no line. Each line keeps `site_code` and loses `at_contract_site`.
- **Masters › Contracts** (§ 5.10).
  - The list answers `sites` (every site) and three top-level flags: `can_add`, `can_read_callout` and
    `can_read_cost`.
  - The Site filter keeps the contracts that have a machine at that site.
  - The *Sites* column and the phone line show the codes.
  - The dialog has no Site field.
- **Add machine** takes a machine of any site inside the adder's units (§ 5.4). The site refusal is gone.
- **The card** shows every contract on the node or its ancestors, wherever the contract's other machines
  stand. The card reads the global permissions.
- **Overlaps** show every other contract (§ 5.3).
- **Renewal** (§ 5.5).
  - There is no site lock and no inactive-site refusal, and `validate_renewal` is removed.
  - Every line except a scrapped one is copied, at any site.
  - The notice reads "Prices start empty: the managers enter them on the new contract."
- **Reminders** (§ 5.6, Q1 a, Q2 a).
  - Push and email go to the key holders at the sites of the contract's machines. One query does this
    (`alerts.people_with_role_at_sites`, `SELECT DISTINCT`).
  - A contract with no line goes to the holders at every site.
  - The texts name the sites: "Contract ends in 60 days · BRICKS, SMTW". The email has a *Sites* line.
  - *What you will get* reads "Contracts ending for machines at SMTW".
- **Breakdown calls** (§ 5.7). `complete` is true only when the reader holds `ticket:read` at every active
  unit of each line site. The vendor warning is counted per line site. The answer carries `warning_sites`
  and `site_codes` and no longer carries `site_code`.
- **Documents** (§ 5.9, Q3 a).
  - Every contract document route checks `contract:read_senior` by the union.
  - Restore and purge need `equipment:purge_documents`, held at any site.
  - The removed list shows contract rows to the holders of `read_senior`. Those rows have no unit.
- **Screens**: the ten frontend files of § 3. `EquipmentPicker` loses its `siteId` and `emptyText` props, and
  its label stays "Equipment".

## 2. How it works

- **v50**: it runs eight steps in order (§ 4.1).
  - Steps 1–3 are v42's texts.
  - Step 4 creates `contracts` in its final shape. The column order is v47's without `site_id`, so a
    converged table and a fresh table compare equal.
  - Step 5 is seven convergence statements: add the v46 columns, add v47's unique key, drop
    `ix_contracts_renewal_of`, drop `fk_contracts_site` (before its column), add `ix_contracts_active_to`,
    drop `ix_contracts_site` by name, and drop `site_id`.
  - Steps 6–8 are the texts of v44 and v45.
  - Each statement can run twice, so a half-applied v50 runs again cleanly.
- **Sites on read**: `_CONTRACT_FROM` joins a subquery: `GROUP_CONCAT(DISTINCT s.code ORDER BY s.code)` over
  `contract_equipment` and `LINE_SITE_JOINS`. `_contract_out` splits the result on the comma. A site code
  cannot hold a comma (`SITE_CODE_RE`). The joins follow `NODE_JOINS`' path (`COALESCE(gp.unit_id, p.unit_id,
  e.unit_id)`), so a machine that moves counts at its new site from then on.
- **Flags**: `_flags()` replaces `_SiteFlags`. Each route works the flags out once and passes them on, so
  every contract in one answer gets the same flags.
- **Access**: `_lock_contract` keeps its fail-closed `has_perm(READ_BASIC)` 404, then calls `check_perm(key)`.
  `change_contract` now uses `_lock_contract` instead of a copy of it (Decisions taken). `get_contract` and
  `contract_calls` answer 404 only for a missing contract.
- **Reminder recipients**: `read_alert_contract` adds `site_ids` and `site_codes` from `LINE_SITES_SQL`.
  `contract_recipients` passes those ids to `people_with_role_at_sites`; with no line it passes every site id.
  `_people_with_role` now takes a list of sites and returns `[]` when the list is empty, so there is no empty
  `IN ()`. `people_at_unit` passes `[site_id]`.
- **Vendor warning**: `_vendor_reach(cur, vendor_id, sites)` returns `(linked, {code: assignable})`.
  `vendor_warning` returns `None`, `("no_linked", [])` or `("no_assignable", sorted codes with 0)`.

## 3. Files touched

**Backend (11 files)**
- `backend/local_db.py`: v42–v47 are replaced by v50 (§ 4.1), with its comment. The header comment now names
  the third squash and the second fixture.
- `backend/config_rbac.py`: the four contract keys leave `SITE_SCOPED`. Their comment says "Global (S087)".
- `backend/auth_utils.py`: `sites_holding` is removed.
- `backend/contracts_core.py`:
  - `site_id` is out of `REQUIRED` and `_CONTRACT_FIELDS`;
  - `SITE_KEPT`, `SITE_INACTIVE`, `renew_site_inactive` and `validate_renewal` are removed;
  - `covered_sql(coverage, today)`;
  - `renewal_lines` skips only scrapped lines;
  - `vendor_warning(linked, {code: count})`;
  - new `LINE_SITE_JOINS` and `LINE_SITES_SQL`.
- `backend/contracts.py`:
  - every access check is now global, and `_flags()` replaces `_SiteFlags`;
  - `site_codes` comes from a subquery, and `_LINE_SELECT` no longer selects `site_id`;
  - the list's filter, `sites` and flags (§ 5.10);
  - Add machine, the overlaps, renewal and the calls (`_vendor_reach`, `_sees_covered_sites`);
  - the document functions (`_contract_id_row`);
  - the docstrings, and the ACCESS and LOCK ORDER notes (§ 5.8).
- `backend/alerts.py`:
  - `_ALERT_CONTRACT` no longer joins `sites`;
  - `read_alert_contract` adds `site_ids` and `site_codes`;
  - `people_with_role_at_sites` replaces `people_with_role_at_site`;
  - `_people_with_role` takes a list of sites (`DISTINCT`);
  - `contract_recipients` uses the line sites, or every site when the contract has no line;
  - the docstring changes.
- `backend/alerts_core.py`:
  - `contract_facts` and `contract_text` use `site_codes`;
  - `you_get` reads "Contracts ending for machines at …";
  - the comment on `CONTRACT_AUDIENCE_KEY` changes.
- `backend/email_core.py`: `contract_ending_email` puts the sites in brackets in the subject and on a *Sites*
  line; with no line, both are left out.
- `backend/task_handlers.py`: the docstring of `contract_alert`.
- `backend/documents.py`:
  - the removed list's contract branch has no site join, and `unit` is None;
  - the branch is added when `has_perm("contract:read_senior")`;
  - the comments and the docstring.
- `backend/equipment.py`: the Contract filter calls `covered_sql(coverage, today)`; the `sites_holding`
  import is gone; the contracts bullet of the LOCK ORDER note.

**Frontend (10 files, by a fork of this coder run)**
- `frontend/src/views/masters/ContractsPanel.vue`:
  - the top-level flags;
  - the Site filter lists every site, an inactive one with " (inactive)";
  - the *Sites* column and the phone line;
  - no Site in the dialog.
- `frontend/src/views/contracts/ContractFields.vue`: no Site field and no `sites` or `siteCode` props. The
  cost-note help reads "Only the managers see this note."
- `frontend/src/views/contracts/ContractRenewDialog.vue`: no `site_id`, the new `renewalNotice` call, no
  `:site-code`.
- `frontend/src/views/contracts/ContractMachineDialog.vue`: no `:site-id` and no `:empty-text`. The price
  help reads "Only the managers see it."
- `frontend/src/views/ContractView.vue`:
  - the header reads "vendor · BRICKS, SMTW", or the vendor alone;
  - "Contract not found.";
  - no "Now at …" line;
  - the documents line reads "Only the managers see these documents and photos."
- `frontend/src/views/contracts/BreakdownCallsCard.vue`: the warning names `warning_sites`.
- `frontend/src/views/equipment/UnderContractCard.vue`: `canRead` and `canEdit` come from the global
  `userPermissions`.
- `frontend/src/utils/contractLabels.js`:
  - `contractBody` and `contractForm` without `site_id`;
  - `renewalNotice(renewal, canReadCost)`;
  - `vendorWarningText(warning, vendorName, siteCodes)`;
  - new `siteCodesText`.
- `frontend/src/views/settings/RemovedDocuments.vue`: a contract row shows its number alone.
- `frontend/src/components/EquipmentPicker.vue`: the `siteId` and `emptyText` props and the `site_id`
  parameter are gone. The empty text is fixed: "No equipment found at your units." The label "Equipment"
  is kept.

**Tests (20 written, 6 removed)**
- New: `backend/tests/fixtures/migrations_v47.py` (frozen v42–v47, copied verbatim from `local_db.py` at
  f5bbb38) and `backend/tests/test_migration_v50.py` (19 tests, § 8.1).
- Removed: `test_migration_v42.py` … `test_migration_v47.py`.
- Changed:
  - `test_migration_squash_v41.py`: `test_production_s_v41_gets_v50`;
  - `test_contracts_api.py`, `test_contracts_core.py`, `test_contract_equipment_api.py`,
    `test_contract_card_api.py`, `test_contract_calls_api.py` and `test_contract_renewal_api.py`;
  - `test_contract_alerts.py`, `test_alerts_core.py`, `test_email_core.py` and `test_push_api.py`;
  - `test_rbac.py`, `test_documents_api.py`, `test_removed_documents_api.py` and `test_equipment_api.py`;
  - `frontend/tests/contractLabels.test.js`;
  - `frontend/e2e/contracts.spec.js` and `frontend/e2e/notifications.spec.js`.

**Docs**: `docs/schema/notes.json`, `schema.json`, `schema-data.js`, `docs/Plan.MD` and `.claude/CLAUDE.md`
(§ Docs updated).

## 4. Decisions taken

- **The calls answer carries both `warning_sites` and `site_codes`.** § 3 says "answers `site_codes` and
  `warning_sites` instead of `site_code`", and § 5.7 names only `warning_sites`. I followed § 3. The screen
  reads only `warning_sites`, and `ANSWER_KEYS` in `test_contract_calls_api.py` lists both.
- **`change_contract` now uses `_lock_contract`.** The old route held its own copy of the lock and checks.
  The new code would have been the same lines, so I reused the function (DRY). The behaviour is § 5.1's
  table: 404 when missing, 403 `FORBIDDEN_TEXT` without `contract:edit`.
- **`_vendor_reach` runs two plain queries**: the linked count, then one `GROUP BY ms.site_id` over the line
  sites. A site with no row counts as 0. With no line, it skips the second query.
- **A contract with no line** gets `complete` true and no `IN ()`. `_sees_covered_sites` returns True for an
  empty site list, as § 5.7 says.
- **`_people_with_role` returns `[]` for an empty site list.** This guard comes before the SQL. Only a
  database with no site at all can reach it (§ 5.6).
- **The list's WHERE** is `1 = 1` when no filter applies. This can happen only with `status=all` and
  inactive contracts shown, because the status default always adds a bound.
- **v50's description** is "Vendors and contracts, company-wide (S079–S085, S087)". It shows in
  `db_version` and Settings › Database.
- **Test run names**: three agents ran backend tests at the same time, so each took its own run name:
  `s087c1` (mine), `s087c1a` and `s087c1b` (the two test forks). The full run and the schema docs used
  `s087c1`.
- **Frontend, by the fork**:
  - with no line, the desktop *Sites* cell shows "—", and the phone line and page header leave the sites out;
  - a removed contract row with no number shows no second line;
  - *Type* keeps its half-width cell, alone in the dialog's first row;
  - the optional test "S087: the Add contract dialog has no Site field and saves" is folded into
    "S080: the engineer adds a contract and sees it In force in Masters › Contracts" (§ 8.4 allows this).
- **Tests, by the forks**:
  - `test_contracts_api.py` gets a `machine_at` fixture, and `add(..., on=machine)` puts each contract on a
    machine, because a contract's site now comes from its lines;
  - a priced line is added with `keycloak_admin`, because IT admin's price is dropped (correct behaviour);
  - in `test_contract_calls_api.py`, the brief's 404→200 flip is named
    `test_a_manager_of_another_site_reads_the_card`.

No departure from the brief's rules.

## 5. Not done, deferred or assumed

- `docs/roadmap/R02-amc-contracts.md` is not edited. The orchestrator records the reversal of Q1.5 there
  (§ 3 Docs).
- **Known red outside the step**: `e2e/changelog.spec.js:14` (S048 changelog, an empty 0.1.14 section). It
  is not fixed here, as the orchestrator asked.
- **Assumed**: production is at v41 and holds none of v50's tables (§ 9 A1). § 8.1's production test proves
  the v41→v50 path on a v20–v41 build with rows.
- **No WebKit run**: no shared frontend file changed (§ 8.4).

## Manual checks

**Runs**:
- **Targeted**: `tooling\run-e2e-tests.bat e2e/contracts.spec.js e2e/notifications.spec.js e2e/screens.spec.js`
  (§ 8.4: the screens and APIs the step changed, plus `screens.spec.js`). Result: 81 passed, 4 skipped,
  0 failed (144 s, the first run).
- **Whole suite at Normal, once**: `tooling\run-e2e-tests.bat`. Result: 370 passed, 15 skipped, 2 failed
  (281 s).
  - Both failures are the known red outside the step:
    `[desktop-chromium] e2e/changelog.spec.js:14 S048: it_admin opens the change log from the version in the
    sidebar` and `… admin opens …` (S048's changelog, the empty 0.1.14 section). They are not fixed here.
  - No WebKit run, because no shared file changed.

**Automated** (from the passing runs above):
- [auto] **important** The engineer of SMTW sees and edits a contract whose machine is at BRICKS — frontend/e2e/contracts.spec.js::S087: the engineer of SMTW sees and edits a contract whose machine is at BRICKS
- [auto] **important** The manager adds machines of SMTW and BRICKS to one contract; the page and the list show BRICKS, SMTW — frontend/e2e/contracts.spec.js::S087: the manager adds machines of SMTW and BRICKS to one contract; the page and the list show BRICKS, SMTW
- [auto] The Site filter lists the contracts with a machine at that site — frontend/e2e/contracts.spec.js::S087: the Site filter lists the contracts with a machine at that site
- [auto] The engineer's Add machine does not offer a machine outside their units ("No equipment found at your units.") — frontend/e2e/contracts.spec.js::S087: the engineer's Add machine does not offer a machine outside their units
- [auto] The Add contract dialog has no Site field and saves — frontend/e2e/contracts.spec.js::S080: the engineer adds a contract and sees it In force in Masters › Contracts
- [auto] No Site field for the engineer, the manager or IT admin — frontend/e2e/contracts.spec.js::S080: the engineer sees the call-out number field and no cost note; the manager sees both, and frontend/e2e/contracts.spec.js::S080: IT admin adds a contract without the call-out number or the cost note
- [auto] The *Sites* column and the phone line fit a phone — frontend/e2e/contracts.spec.js::S080: the Contracts list fits a phone with no sideways scroll (`@device`, phone and desktop)
- [auto] The removed contract document's row shows no site; "Only the managers see these documents and photos." — frontend/e2e/contracts.spec.js::S083: a manager removes a contract document and restores it from Settings
- [auto] The renewal notice "Prices start empty: the managers enter them on the new contract." — frontend/e2e/contracts.spec.js::S085: the engineer renews a contract; the new contract opens with its terms and machines, and the chain shows on both pages
- [auto] The page header shows the vendor alone for a contract with no machine — frontend/e2e/contracts.spec.js::S085: an inactive vendor is refused on renewal beside the Vendor field
- [auto] The vendor warning names the sites ("… can be assigned at SMTW. …") — frontend/e2e/contracts.spec.js::S086: the contract page warns when no Team record is linked to the vendor
- [auto] *What you will get*: "Contracts ending for machines at SMTW" (and ", by email") — frontend/e2e/notifications.spec.js::S021 A1: What you will get — the engineer's breakdowns and defects, the technician's assigned jobs, and frontend/e2e/notifications.spec.js::S032: the manager sees the closed-ticket email line and their address; Send test email says it is on its way

**On a real device**: none (§ 8.5).

## Docs updated

- `docs/schema/notes.json`:
  - the `contracts` line: company-wide, no `site_id`, `ix_contracts_active_to`;
  - the `contract_equipment` line: a node of any site, inside the adder's units;
  - the `equipment_documents` line: "only by a manager (S083 E2, S087)".
- `docs/schema/schema.json` and `docs/schema/schema-data.js` are generated by `tooling\schema-docs.bat
  write`. The diff is exactly § 8.1's: `"migration"` 47→50, no `site_id`, no `fk_contracts_site`, and
  `ix_contracts_site` replaced by `ix_contracts_active_to`. `check` exits 0 (4 passed, run `s087c1`).
- `docs/Plan.MD`:
  - § 2 item 9: `contract:read` is "engineers and managers, of any site: the keys are company-wide, S087",
    and `read_senior` is "managers";
  - § 6 *Contract reminders*: the holders "at the sites of the contract's machines".
  - The gate-A sentence was already added by the orchestrator.
- `.claude/CLAUDE.md`:
  - *Files (S006)*: the contract owner, with no site;
  - *RBAC deviation*: the four contract keys are global;
  - *Migrations (S025, S088, S087)*: the v50 sentence and both fixtures;
  - *Notifications*: the S084 sentence and `people_with_role_at_sites` (twice);
  - § SMTW-Review: *Migrations*, *Contract fields by key*, *Contract reminders*, *Contract renewal* and
    *Breakdown calls*;
  - § SMTW-Review: the new point *Contracts across sites (S087)*, in § 8.6's words.
  - The version mentions (v46), (v47) are kept, as the brief says.
- `docs/steps/device-checks.md`: no row, because § 8.5 lists no real-device check.
- `backend/example_secrets_app.py` and `docs/Keycloak.md`: no change, because no secret, role or claim
  changed.

## Feedback

- waste: a stray `cat > /dev/null` that I typed waited on stdin until the Bash tool's 120 s limit, and then I
  had to stop it (2 min).
- idea: the steps that only rename across many test files (§ 8.3: 14 files) split well into forks with their
  own `YANTRA_TEST_RUN` names (`s087c1a`, `s087c1b`). The README's rule "your own test run name" could say
  that a coder's parallel forks each take a suffix (3 groups ran at once here, about 4 min each).
- hindrance: `git rm` stages the deletions, and the rule "commits are the user's" suggests the index is his
  too, so I had to unstage (`git reset -- …`). The removed test files could be deleted with plain `rm`; the
  README could say which (1 extra command).

## Fix rounds

### Round 1

**CR1-01 (blocker): Fixed.** `backend/tests/test_alerts.py::TestFanOut::test_push_kinds_queue_push_only_even_for_people_with_an_address`
now looks for `email_send` rows of this plant's two people with an address (manager, engineer: payload
`person_id`) instead of every `email_send` row in the queue. I chose narrowing over emptying the queue: the test
keeps its meaning (these two people, who have an address, still get no email for a push-only kind) and it no
longer depends on what another class left on the worker.
- Fails without the fix: ran `YANTRA_TEST_RUN=s087f1 tooling/run-backend-tests.bat tests/test_contract_alerts.py::TestHandler tests/test_alerts.py::TestFanOut::test_push_kinds_queue_push_only_even_for_people_with_an_address -n 0` on the old assertion: 1 failed, 13 passed (the `email_send` rows left by `TestHandler`).
- Passes with it: the same command: 14 passed.
- Other tests that count queue rows: `test_alerts.py:179-184` compares a before and after count (a delta), the others filter by `task_type` and ticket, or empty the queue themselves. Nothing else counts rows `TestHandler` leaves. Decision: this edit is in `test_alerts.py`, outside § 3's list.

**CR1-02 (nit): Fixed (stated).** Brief § 8.2's `test_the_texts_name_the_machine_sites` is not its own test. Its checks live in four tests: `test_contract_alerts.py::…test_push_to_the_holders_at_each_machine_site`, `…::test_email_to_the_managers_at_each_machine_site`, `test_alerts_core.py::…test_the_title_names_the_machine_sites` and `test_email_core.py::…test_no_machine_no_sites`. (Same statement as in the review; no code change.)

**CR1-03 (nit): Fixed.** The four `contracts.py` docstring lines (3, 62, 72, 86) are wrapped; no line of the file is over 120 columns now.

**Tests (run name s087f1):** the repro above 14 passed; full `tooling/run-tests.bat`: backend 4467 passed (145 s), frontend 409 passed, tooling 231 passed, ALL SUITES PASSED. No browser run (no frontend change).

**Docs updated:** none, because the round changes one test and docstring wrapping.

## Feedback (fix round 1)
- none

### Round 2 (orchestrator, 31-10-2026)

- CR1-03 (nit, still open after verify review r2): the five long docstring lines of `backend/contracts.py` wrapped at 120 columns by the orchestrator.
- Line endings: seven files had been written with CRLF in the working tree (`backend/contracts.py`, `contracts_core.py`, `email_core.py`, `tests/test_alerts.py`, `tests/test_rbac.py`, `frontend/src/views/masters/ContractsPanel.vue`, `frontend/src/views/settings/RemovedDocuments.vue`); restored to LF, as at HEAD. Their tests re-run: 314 + 138 passed (run s087f1).

## Amendment A1 — Add machine asks for the site first

**What was built.** The *Add machine* dialog shows a **Site** select above the equipment search. Its options are the active sites where the adder has a unit. With one site, it is chosen already. Until a site is chosen, the search is disabled and the hint reads "Choose a site first.". After that, the search lists only that site's machines. Changing the site clears the search and any machine picked. The site is a filter of the screen only and is not sent with the line. No API change.

**How it works.**
- `ContractMachineDialog.vue`: `openAdd()` loads the existing caches (`ensureSites`, `ensureUnits`, `ensureMyUnits`: `GET /api/masters/sites`, `/units`, `/api/equipment/my-units`), then chooses the site if there is exactly one. `siteChoices` comes from the new `unitSites`. The select's `change` calls `changeMachine()`, which clears the picked machine and gives the picker a new key (empty search).
- `EquipmentPicker.vue`: the `siteId` prop is back and adds `site_id` to `GET /api/equipment`; a new `disabled` prop turns the input off.
- `stores/equipment.js`: `unitSites(allUnits, allSites, mine)` is the active sites of the units from `filterableUnits`.

**Files touched (5 code, 2 test).**
- `frontend/src/views/contracts/ContractMachineDialog.vue`
- `frontend/src/components/EquipmentPicker.vue`
- `frontend/src/stores/equipment.js`
- `frontend/tests/readingSites.test.js` (3 tests of `unitSites`)
- `frontend/e2e/contracts.spec.js` (helper `chooseSite`; the Add machine tests choose the site; the new A1 test)

**Decisions taken.**
- No new route: the site list is the masters caches plus `my-units`, the way the readings sheet does it. A new helper `unitSites` (beside `readingSites`) rather than reusing `readingSites`, because that one follows `reading_unit_ids`, not the units the user reads.
- `disabled` is a second picker prop beside `siteId` (the brief names only `siteId`). `emptyText` stays removed: "No equipment found at your units." still fits.
- Option labels are the site code (as on the readings sheet). A user with no unit at any site sees "You have no unit at any site."; a failed load shows the error under the select.
- Departure from brief F10 as A1 states: `siteId` is back. Doc comments of the picker not changed.

**Tests.**
- New test written green alone first (`E2E_LANES=1 … --project=phone-chromium -g "S087 A1"`). Its first run found a real fault: `siteChoices` read `myUnits` before it was loaded and the render threw; fixed with a guard.
- Targeted `tooling/run-e2e-tests.bat e2e/contracts.spec.js e2e/screens.spec.js` (Normal): 69 passed, 1 skipped, 0 failed (4.6 min).
- `YANTRA_TEST_RUN=s087a1 tooling/run-tests.bat`: backend 4467 passed, frontend 412 passed, tooling 231 passed, ALL SUITES PASSED. `npx vite build` in `frontend/`: built.

**Manual checks.**
- [auto] Add machine asks for the site first, the search is off until then and lists only that site — `frontend/e2e/contracts.spec.js::S087 A1: Add machine asks for the site first; the search is off until a site is chosen and lists only that site`
- [auto] The engineer's one site is chosen already and BRICKS is not offered — `frontend/e2e/contracts.spec.js::S087: the engineer's Add machine does not offer a machine outside their units`
- On a real device: none.

**Docs updated:** none, because the change is inside one dialog and one picker prop; Plan.MD, the schema docs and CLAUDE.md name neither, and no real-device check is added.

## Feedback (amendment A1)

- hindrance: a pipe to `tail` made the long Bash e2e run move to the background with an empty output file, so I could not see progress (2 runs, ~5 min waiting); a Monitor call needed its schema loaded first.
- idea: the brief's A1 could have said whether the picker's input is disabled by a prop or hidden, as that was my only real design choice.

### Fix round (A1)

Review: `4-code-review-r3.md`. Three nits, all addressed; CR1-03 needs no change.

- **CR3-01 Fixed.** The A1 e2e test now picks the BRICKS machine, changes the site to SMTW, and asserts `picked-machine` has count 0 before checking the search is empty. Red run not made: the clearing code (`changeMachine`) already existed and was never wrong; the change only adds an assertion for it. The test passes alone on `phone-chromium`.
- **CR3-02 Fixed (docstring).** `unitSites` in `frontend/src/stores/equipment.js` now says that for all-units access it uses any unit of the site, active or not, as `filterableUnits` gives. I did not filter `u.active`: A1 asks for active sites only (the `s.active` filter stays), and the add-line route checks `accessible_unit_ids`, which does not exclude inactive units, so the select offers no site the API would refuse.
- **CR3-03 Fixed.** The Site select in `ContractMachineDialog.vue` is now `form-select form-select-lg`.
- **CR1-03 Already fixed.** No line of `backend/contracts.py` is over 120 columns; nothing touched there.

Tests: `tooling/run-frontend-tests.bat tests/readingSites.test.js` 7 passed. A1 test alone (`E2E_LANES=1`, `phone-chromium`, `-g "A1"`) 1 passed. Targeted `e2e/contracts.spec.js e2e/screens.spec.js` (Normal): 69 passed, 1 skipped, 0 failed (5.0 min).

Docs updated: none, because the change is a docstring, a CSS class and a test assertion.

## Feedback (fix round A1)

- none
