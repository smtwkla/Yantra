```
Step: S087 — Contracts across sites
Doc: brief-review r2
Author: Brief reviewer (Fable)
Date: 31-10-2026
```

Reviewed against: 26810aa + uncommitted edits outside a step (`EquipmentPicker.vue` label "Equipment", `ContractFields.vue` full-width Covered / Not covered, the four e2e specs that follow the label, `docs/steps/INDEX.md`)

**Verdict: no `blocker` or `major` finding is open.** No `minor`; two nits. Every round-1 finding marked `Accepted` is in the brief's text, not only in the Review log. Diffed `scratch/S087-brief-r1.md` against the brief (`git diff --no-index -w`) and re-read the changed text: the header's `Baseline`, § 3 (intro, Backend, Frontend, Tests, Docs, file count), § 4.2, § 5.1, § 5.4, § 5.6, § 5.10, § 7 F2 and F10, § 8.2, § 8.3, § 8.4, § 9 Q5, Q6, A1, A3 and the Review log. The sections that did not change were not re-reviewed. Facts file read: `scratch/brief-facts-S087.md`; it does not list the `TestCoveredSql` test ids, so those were checked in the code.

**The S088 squash (v20–v48 → v50): no clash.** S087 keeps v48 as written; `test_migration_v48.py`, `test_modules.py`'s `LATEST_VERSION` 48 and the `notes.json` phrase "v48 dropped `site_id`" are right for S087 and become S088's to re-number, with § 4.2's "v43–v48 ship together". Nothing in this brief needs to change for it.

## Findings

None at `blocker`, `major` or `minor`.

## Nits

- **BR2-01** (nit) § 8.2 / § 8.3, `test_contracts_core.py`: `TestCoveredSql::test_no_site` (`:349-351`) asserts the `"0 = 1"` / `"1 = 1"` branch that § 5.4 now removes, so it breaks too. Name it in § 8.3 as removed, beside `test_under_and_not_under`.
- **BR2-02** (nit) § 8.3, `test_removed_documents_api.py`: the `case.elsewhere` line of `test_it_admin_may_not_restore_or_purge` is `:539` (the test starts at `:534`), not `:540`.

## Checked and found consistent

- **Round-1 answers in the text.** BR1-01: the three tests are in § 8.3 / § 8.4 and `test_push_api.py` in § 3 (18 files, 39 total). BR1-02: `ContractFields.vue:172` in § 3 and § 5.10; the line reads "Only the managers of this site see this note." today. BR1-03: § 5.10 states *All sites* and the alternative; § 9 Q6 asks KLA. BR1-04: § 8.3 gives the two outcomes; § 8.4 puts a machine on the S086 contract. BR1-05–BR1-13: all in § 3, § 4.2, § 5.1, § 5.4, § 5.6, § 7 F10, § 8.2, § 8.4, § 9 A1 and A3.
- **§ 5.4 / § 3, `covered_sql(coverage, today)`.** `contracts_core.py:317-327` takes `site_ids` today and has the `"0 = 1"` / `"1 = 1"` branch; `equipment.py:670` is its only route caller, behind `require_perm("equipment:read")`; `test_contracts_core.py` is its only test caller (facts file).
- **§ 3, `_LINE_SELECT` (`:223-228`).** `s.id AS site_id` (`:225`) is read only at `:262` (`at_contract_site`); `renewal_lines` (`contracts_core.py:384-399`) reads `at_contract_site` and `site_code` from the lines, so it changes with them as § 3 says ("skips only scrapped lines").
- **§ 5.6, one query.** `people_with_role_at_site` (`alerts.py:182`) has one caller, `contract_recipients` (`:498`), and no test caller; `_people_with_role` (`:189-213`) joins `memberships` on `ms.site_id = %s`, so a `site_ids` list with `IN` and `SELECT DISTINCT` is the right change (a person with memberships at two listed sites would otherwise come twice); `people_at_unit` (`:171-179`) can pass `[site_id]` with its signature unchanged, so `recipients` (`:216`) and the improvement path (`:366`) do not change. The module docstring (`:29`) names the old function; § 3 names the docstring (`:26-37`).
- **§ 8.3, `test_an_engineer_of_another_site` (`test_contract_equipment_api.py:186-192`).** `_check_node` (`contracts.py:541-558`) refuses a node outside `accessible_unit_ids` with 400 `CHOOSE_MACHINE` (`:552`) before the site check that goes; the stranger (engineer at B only) gets that; `operator_here` (operator at `site`) has the node in its units and reaches the insert: 201.
- **§ 8.4.** `contractToRenew` (`contracts.spec.js:660`) defaults `machines = 0`, so the S085 header at `:756` loses " · SMTW"; the S086 test (`:937-949`) asserts `no_assignable` at `:947-949` on a contract with no line (`:940`); `lineByApi` (`:272`) and `machineByApi` exist. `settings.spec.js:88-92`'s one contract line is the task's description, which the brief does not change; `tickets-work.spec.js` and `equipment.spec.js` hold no contract line.
- **§ 3 Frontend, `EquipmentPicker.vue`.** The props are at `:17-18`, the `site_id` parameter at `:39`, the sentence at `:7-8`; the template reads `{{ emptyText }}` (`:65`), so the fixed text replaces it. The callers: `RaiseTicketView.vue:266` and `ReadingsRegister.vue:152` pass neither prop; `ContractMachineDialog.vue:90-91` passes both and § 3 removes them. The uncommitted label change ("Equipment") is not in the brief's scope and does not conflict.
- **§ 3 Docs.** `notes.json:19` ends "a contract's only by the site's manager (S083 E2)"; `.claude/CLAUDE.md` names `people_with_role_at_site` twice in the Notifications bullet (once as `alerts.people_with_role_at_site`, once bare); `test_push_api.py:59` holds `f"Contracts ending at {site['code']}"`.
- **§ 5.1.** The kept `has_perm(READ_BASIC)` 404 is stated with its reason; `IT admin` holds `contract:read_basic` through its token (round 1), so the branch stays unreachable as the text says.
- **§ 4.2 / A1.** Not load-bearing, as asked in BR1-12; no `_PRECONDITIONS` entry either way.

## Feedback

- idea: the facts file's *Test ids* section lists only the ids the brief writes as `file::Class::test`; a test the brief names bare (`TestCoveredSql::test_under_and_not_under`) is not looked up, and its sibling `test_no_site` in the same class was found only by opening the file (BR2-01). Listing the sibling tests of a named class would have shown it.
