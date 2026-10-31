```
Step: S087 — Contracts across sites
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 31-10-2026
```

Reviewed against: 26810aa + uncommitted edits outside a step (`EquipmentPicker.vue` label "Equipment", `ContractFields.vue` full-width Covered / Not covered, the four e2e specs that follow the label)

**Verdict: no `blocker` or `major` finding is open.** Four `minor` findings and nine nits. The brief carries F1, F2 and Q5 out as decided; the migration, the key changes, the lock notes and the RBAC matrix check out against the code. The main gaps are three breaking tests the brief does not list and one site-worded screen text it leaves in place. Facts file read: `scratch/brief-facts-S087.md`. The uncommitted picker label change does not conflict with the brief: the brief never quotes the label, and its rewritten e2e tests only name the picker's empty text, which is the component's own default.

## Findings

### BR1-01 — minor — § 8.3 / § 8.4: three tests that break are not listed

**Problem.** The brief's list of breaking tests misses:
- `backend/tests/test_push_api.py::TestConfig::test_push_on_with_the_public_key_and_what_you_get` (`:59`): asserts `"Contracts ending at {site}"`, which § 5.6 rewords to "Contracts ending for machines at …".
- `backend/tests/test_removed_documents_api.py::TestContractRows::test_it_admin_may_not_restore_or_purge` (`:540`): its last line asserts that `case.elsewhere` (a manager of another site) gets 404 on restore; after § 5.9 that is 200.
- `frontend/e2e/contracts.spec.js` `S085: an inactive vendor is refused on renewal beside the Vendor field` (`:756`): asserts the header `${other.name} · SMTW`. `contractToRenew` makes a contract with no machine (`machines = 0`, `:660`), so after § 5.10 the header is the vendor alone.

**Why it matters.** The coder plans its work from § 8.3; a test found only by the red run costs a fix round. § 3's test count (17 files) is also one short: `test_push_api.py` is an 18th.

**Options.** (a) Add the three to § 8.3 / § 8.4 and `test_push_api.py` to § 3 — **recommended**. (b) Leave them to the run.

### BR1-02 — minor — `ContractFields.vue:172` keeps a site-worded help text

**Problem.** The cost note's help text reads "Only the managers of this site see this note." (`ContractFields.vue:172`, the `v-else` under the Cost note field). The brief changes the Site field and the props (`:8`, `:19-20`, `:50-58`) but not this line. After S087 there is no "this site": every manager sees the note.

**Why it matters.** The text would tell a manager the note is private to one site when it is not (ISO 27001 A.5.15 is about telling the user what the gate is). The brief fixes the sibling texts (`ContractView.vue:266`, `ContractMachineDialog.vue:108`, `renewalNotice`) but misses this one.

**Options.** (a) Add to § 3 and § 5.10: "Only the managers see this note." — **recommended**, the same form as the brief's other replacements. (b) Drop the line (the "Managers only" heading above it already says it).

### BR1-03 — minor — the list's default scope for a one-site engineer (a judgement call for KLA)

**Problem.** Today an engineer of one site opens Masters › Contracts and sees that site's contracts only (`list_contracts` over `sites_holding`). After § 5.10 the list opens on *All sites* for everyone, and a BRICKS engineer scrolls past SMTW's contracts to find theirs. F7 keeps the Site filter because "a site's engineer wants theirs", but nothing preselects it.

**Why it matters.** Use on the floor: the person scanning the list is usually a site's engineer; the new default makes their list longer. With tens of contracts and a *Sites* column it stays readable, so this is a judgement, not a fault.

**Options.** (a) Keep *All sites* as the default — **recommended**: one rule, no per-user state, a contract with no line is never hidden by default, and the user's own site is one tap away. (b) Preselect the Site filter to the user's site when they hold a membership at exactly one site (`auth` store's `membership_sites`); a contract with no machines, or with machines elsewhere, is then hidden until the filter is cleared. Record the choice in § 5.10 either way, so the coder does not decide it.

### BR1-04 — minor — § 8.3 says "flips" where the new outcome is not the obvious one

**Problem.** Two entries leave the coder to work out the new assertion:
- `test_contract_equipment_api.py::test_an_engineer_of_another_site` (`:186-192`) "(flips)": the stranger (engineer of B only) no longer gets 403, but not 201 either: `_check_node` refuses the A machine as outside their units, 400 `CHOOSE_MACHINE`. `operator_here` (engineer of B, operator at A) gets 201: edit is global, and the node is inside their units (the brief's own example in § 5.4).
- e2e `S086: the contract page warns when no Team record is linked to the vendor` (`:948`) "the text with the sites, if it shows `no_assignable`": it does (`:947-949`), and the contract has no machine (`:940`). Under § 5.7 a contract with no line can show only `no_linked`, so the test must put a machine on the contract (`lineByApi`) before the `no_assignable` step, or that assertion never passes.

**Why it matters.** A hedged entry reads as "check and see"; the coder may assert 201 for the stranger, or drop the `no_assignable` step.

**Options.** (a) State the new outcomes in § 8.3 / § 8.4 as above — **recommended**. (b) Leave to the run.

## Nits

- **BR1-05** (nit) § 3 first paragraph: "S080–S086 are coded and at gate B (not committed); this brief cites `file:line` from `refs/steps/S086`" is stale: they are committed (f0343d0, status commit 26810aa). Say the lines are from HEAD, and set the brief's `Baseline:` to 26810aa at approval.
- **BR1-06** (nit) § 5.4 / `equipment.py`: `covered_sql(coverage, can_read, today)` keeps a parameter that is always true: a caller has passed `require_perm("equipment:read")`, every site role holds `contract:read_basic` (`("*",)`), and IT admin's token grants it (`compute_permissions`). Drop it: `covered_sql(coverage, today)`, and the `"0 = 1"` / `"1 = 1"` branch with it; `test_covered_sql_without_read` goes too.
- **BR1-07** (nit) A3 against F10: after S087 `EquipmentPicker`'s `siteId` and `emptyText` props have no caller (the three callers pass neither). F10 removes `sites_holding` and `validate_renewal` for the same reason; apply one rule and decide it in the brief, not by the code reviewer.
- **BR1-08** (nit) § 3 `contracts.py`: the module summary (`:1-15`: "at one site", "node of the contract's site", "at the old one's site", "machines of the site") changes too, not only `:19-102`; also `_renewal_links`' docstring (`:318-319`, "contracts of the same site"), `_LINE_SELECT`'s `s.id AS site_id` (`:225`, used only by `at_contract_site`), and the docstrings of `UnderContractCard.vue:9-10`, `ContractView.vue:14`, `BreakdownCallsCard.vue:11-12`, `ContractsPanel.vue:4-9`.
- **BR1-09** (nit) § 3 Docs, `docs/schema/notes.json`: the `equipment_documents` line (`:19`) ends "a contract's only by the site's manager (S083 E2)" → "by a manager"; add it to the two lines the brief names.
- **BR1-10** (nit) § 5.6 recipients: a loop over `people_with_role_at_site` per site, then a merge that drops duplicates, is more code than one query. Give `_people_with_role` a `site_ids` list (`ms.site_id IN (…)`, `SELECT DISTINCT p.id … ORDER BY p.id`) and rename `people_with_role_at_site` → `people_with_role_at_sites`; the no-line case passes every site's id the same way. Also say whether `SELECT id FROM sites` takes inactive sites (every site is simplest; say so).
- **BR1-11** (nit) § 8.4 Runs: `tickets-work.spec.js` and `equipment.spec.js` hold no contract test (`git grep -l contract frontend/e2e` → `contracts`, `masters`, `settings`; the ticket line, the card and the removed row are all in `contracts.spec.js`; `settings.spec.js`'s one line is the task name, unchanged). The targeted run can be `contracts`, `notifications`, `screens`.
- **BR1-12** (nit) § 4.2 / A1: say that the plan holds even if a release goes out between S086 and S087 (v48 then drops `site_id` with its values, which is the decision: the site is no longer a fact of the contract), so A1 is not load-bearing and still no precondition is needed.
- **BR1-13** (nit) § 5.1 table, `_lock_contract` and `_contract_access`: the `has_perm(READ_BASIC)` 404 branch is unreachable behind `require_perm(EDIT)` and `documents._owner_key` (every holder of `edit`, `read_senior` or `purge_documents` holds `read_basic`). Keep it as the fail-closed habit or drop it; say which, so the coder does not wonder.

## Checked and found consistent

- F1, F2 and Q5 (decided by KLA) are carried out as decided; the brief does not reopen them.
- `has_perm_at`, `require_perm_at`, `access_core.has_key_at` and `user_unit_ids` assert the key is in `SITE_SCOPED` (`auth_utils.py:435, :486`; `access_core.py:101, :125`), so every contract call of them must go, as § 5.1 says; the table's rows match the code (`contracts.py:176-193, :295, :338-349, :380-426, :441-465, :470-513, :520-528, :590, :626-646, :789, :819-831, :851-856`; `equipment.py:670`; `documents.py:669-673`).
- `sites_holding` has the four callers the brief names and no test caller; `check_perm` and `FORBIDDEN_TEXT` exist as cited.
- Holders unchanged: `test_role_matrix` compares per-role key sets only (`test_rbac.py:267`), so it stays green; `test_contract_keys:134` is the one line that changes. IT admin's token grants `contract:read_basic` and `contract:edit`, so `has_perm` gives IT admin what `has_perm_at` gave; fail-closed unchanged (`compute_permissions` gives `("*",)` keys only to a role in `ROLES`).
- Migration v48: `DROP FOREIGN KEY IF EXISTS`, `ADD KEY IF NOT EXISTS`, `DROP INDEX IF EXISTS`, `DROP COLUMN IF EXISTS` are the forms v45 and v47 already use; the order (foreign key, new key, old key by name, column) is right, each statement is a no-op on a re-run, and dropping the index by name avoids a leftover `ix_contracts_site (active, to_date)`. v43 is not edited. `test_migration_v47.py`'s shape (`range(20, 48)`, `_keys`, `_foreign_keys`, `_a_v42_database_with_a_site_and_a_vendor`, `_add_contract`) fits the planned v48 tests; v44 and v45's tests insert `site_id` into databases migrated only to their own version, so they stay green. Production holds no contract (last tag v0.1.14 = e77d635, before v43).
- Lock order after S087 (§ 5.8): no contract write locks a site row; the create holds the vendor shared then inserts; the renewal holds the old contract exclusive, the vendor shared, nodes (1) shared in id order; the `equipment.py:69-81` and `contracts.py:98-101` bullets named are the ones that mention the site lock. The new reads (`LINE_SITES_SQL`, the `site_codes` subquery) are plain.
- `LINE_SITE_JOINS` repeats `NODE_JOINS`' unit path without the `equipment_classes c` alias, so it can sit in `_CONTRACT_FROM` beside `contracts c`; `alerts.py` may import `contracts_core` (no cycle: `alerts_core.py:21` already does).
- Reminder recipients (Q1 a, Q2 a) match `you_get`'s new line and `CONTRACT_AUDIENCE_KEY`; the texts carry no gated field; the scan and markers are untouched.
- The e2e rewrite of `S081: a machine of another site is not offered…` and the uncommitted label change do not conflict: the brief names the picker's default empty text "No equipment found at your units." (`EquipmentPicker.vue:18`), not the label.
- Standards: ISO 55001 § 8.3 (outsourcing), ISO 27001:2022 A.5.15 (access control) and ISO 9001:2015 § 7.5.3 (documented information) are named, explained in plain words, and the deliberate widening of A.5.15 is stated as KLA's decision.
- Manual checks: none on a device is right (a field gone, a column, texts); the automated list marks the two important flows; each new flow test calls `expectDialogFits`.
- Plan.MD `§ 2 item 9` (`:48`) and the S084 line in § 6 (`:923`) hold the phrases the brief replaces; the `.claude/CLAUDE.md` lines named (*Files*, *RBAC deviation*, *Notifications*, the five SMTW-Review points) hold the phrases the brief drops.
- Track: full is right (a migration, RBAC keys, lock notes, 39 files).

## Feedback

- hindrance: the facts file (730 lines, ~26k tokens) is over the Read tool's page cap, so it took two reads; a facts file could print the *Code names* section without the "used in N code files" lines for names the brief marks **(new)** or that are plain words (`site_id`, `to_date`, `canEdit`: 20+ definitions each, no use to the reviewer).
- idea: a facts section "test lines that use a name the brief removes" (`site_code`, `at_contract_site`, `SITE_KEPT`, "Contracts ending at", `· SMTW`) would have listed BR1-01's three missed tests directly; today that is a hand grep per name across `backend/tests` and `frontend/e2e`.
