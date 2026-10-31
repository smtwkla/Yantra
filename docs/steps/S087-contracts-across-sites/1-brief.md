```
Step: S087 — Contracts across sites
Doc: brief
Author: Orchestrator's drafter (Opus)
Date: 31-10-2026
Track: full
Baseline: f5bbb38 (HEAD: S088 committed 31-10-2026), checked by staleness review s1
Status: Done (committed at adoption, 31-10-2026; no device check; A1 approved by the request of KLA, reviewed r3, 3 nits fixed); was: Gate B 31-10-2026 (code review r1: 1 blocker (a test-order fault from S084), 2 nits; fixed in fix round 1 and by the orchestrator; verify review r2: no blocker or major); approved 31-10-2026 by KLA (all recommended answers, § 9); was: Gate A 31-10-2026 (review r1: 4 minor, 9 nits; r2: 2 nits; r3: 1 minor, 6 nits; all accepted; 0 blocker, 0 major)
```

# S087 — Contracts across sites

## 1. What will be built

S080–S086 (roadmap R02) built the contract register on one rule: **one site per contract** (R02
Q1.5 a; Plan.MD § 2 item 9). KLA, 31-10-2026: "A contract may not be restricted to equipment from
one site. Remove it from contract master. Each equipment record can have a site, if needed. For ex,
UPS from multiple sites will be given in one contract." This step removes the contract's site.

1. **The contract has no site.** Migration **v50** replaces v42–v47 with one squashed entry holding
   the final R02 schema, without `contracts.site_id`, its foreign key and its key (§ 4; KLA,
   31-10-2026). It comes after S088, which squashes v20–v41 into v41 and is coded first. Each machine on the contract keeps its own site through its unit (`NODE_JOINS`,
   `backend/equipment.py:194`): that is "each equipment record has a site".
2. **The contract keys are company-wide** (KLA, decision 1, § 7 F1). `contract:read_basic`,
   `contract:read`, `contract:read_senior` and `contract:edit` leave `config_rbac.SITE_SCOPED` and are
   checked by the union (`has_perm`, `require_perm`, `check_perm`). An engineer of any site reads every
   contract's call-out number and edits every contract; a manager of any site reads every price, cost
   note and document.
3. **Add machine takes a machine of any site**, still only one inside the adder's units and not
   scrapped. The refusal "Choose a machine of SMTW, the contract's site." goes.
4. **The sites of a contract are its machines' sites**, derived on every read, never stored: the
   contract page shows "Atlas Copco · BRICKS, SMTW"; Masters › Contracts has a **Sites** column; the
   **Site** filter lists the contracts with a machine at that site.
5. **The dialog loses its Site field** (Add, Edit, Renew).
6. **Reminders** (S084) go to the key holders at the sites of the contract's machines (§ 5.6; KLA to
   confirm, § 9 Q1). **Breakdown calls** (S086) count as complete for a reader who sees every unit of
   those sites (§ 5.7). **Renewal** (S085) copies every machine not scrapped, wherever it is (§ 5.5).

**After S087:** the engineer enters one AMC "VP Power UPS AMC 2026–27" and adds the UPS of SMTW,
BRICKS and SMTW-KP to it; each UPS's page shows the card; the page header reads "VP Power · BRICKS,
SMTW, SMTW-KP"; the reminders reach the engineers and managers of all three sites.

### Out of scope

- A per-site split of the cost (D8's price stays per machine line; R02.8's report sums by machine).
- Any change to who may log in or which units a person sees (S011).
- Read-only contracts after their end (S085 Q1), *Edit* on the contract page (S085 Q4).
- Making `equipment:purge_documents` or another key global: only the four contract keys move.

## 2. Standards and practice

- **ISO 55000 / ISO 55001, asset management** (§ 8.3 outsourcing, as S080–S086 cite it; the clause
  number in the 2024 edition *to verify*). In plain words: the organisation manages its assets as one
  portfolio and keeps control of the work it gives to outside firms. One service agreement over assets
  at several locations is normal practice (a UPS or forklift AMC for a whole company); the record of
  which assets it covers stays per asset. Each line still names one machine with its site, so the
  asset register stays the single source of where a machine is.
- **ISO/IEC 27001:2022 A.5.15, access control.** In plain words: each person sees only what the work
  needs, and the server enforces it. **A deliberate, owner-approved widening:** the call-out number,
  the price, the cost note and the documents now follow their keys at every site, not only at the
  contract's site (KLA, 31-10-2026, who accepted that a manager of one site sees another site's prices).
  The gate stays on the server, in one place (`contracts._contract_out`, `_drop_gated`); IT admin
  still reads neither gated field; a request with no identity still gets 401, a login with no site
  role 403 (fail-closed unchanged); admin by the bypass, unchanged.
- **ISO 9001:2015 § 7.5.3, control of documented information.** In plain words: keep records
  retrievable and protected from unintended change. Contracts stay never deleted (set inactive);
  each line add and remove keeps its history line on the machine; nothing in this step removes a
  stored record. v50 drops `site_id` only on dev and test databases; production never held it (§ 4.2).

## 3. Where

S080–S086 are committed (f0343d0, status commit 26810aa); this brief cites `file:line` from HEAD
and names functions beside the lines. Names marked **(new)** do not exist yet.

### Backend (11 files)

- `backend/local_db.py`: v42–v47 (`local_db.py:1140-1281`) are replaced by one entry **v50** after
  S088's v41 (§ 4.1), with its comment; no `_PRECONDITIONS` entry (`:1307`; § 4.2).
  `LATEST_VERSION` follows the last entry (`_MIGRATIONS[-1][0]`), so it becomes 50 with no edit. The
  header comment S088 wrote (`local_db.py:52-70`) keeps "then the later versions run" and "New
  migrations continue after the last entry"; any line of it that names v42–v47 names v50.
- `backend/config_rbac.py`: the four keys leave `SITE_SCOPED` (`config_rbac.py:231-235`); the comment
  at `config_rbac.py:157-162` says "Global (S087): a contract has no site". Holders unchanged.
- `backend/auth_utils.py`: `sites_holding` (`auth_utils.py:451-456`) is removed: its four callers
  (`contracts.py:295`, `contracts.py:386`, `documents.py:669-670`, `equipment.py:670`) all go (§ 5.1).
  No test calls it.
- `backend/contracts_core.py`: `REQUIRED` and `_CONTRACT_FIELDS` lose `site_id`
  (`contracts_core.py:45`, `:99`, `:115`); `SITE_KEPT`, `SITE_INACTIVE` (`:39-40`), `renew_site_inactive`
  (`:340-342`) and `validate_renewal` (`:350-359`) are removed; `GATED_FIELDS`' comment (`:141`) loses
  "at the contract's site"; `covered_sql` (`:317-327`) loses `site_ids`: `covered_sql(coverage,
  today)` (§ 5.4);
  `renewal_lines` (`:384-399`) skips only scrapped lines; `vendor_warning` (`:448-455`) takes the
  assignable counts per site (§ 5.7); new `LINE_SITE_JOINS` **(new)** and `LINE_SITES_SQL` **(new)**
  (§ 5.2).
- `backend/contracts.py`: every site check becomes global (§ 5.1, list below); `_SiteFlags`
  (`contracts.py:176-193`) becomes `_flags()` **(new)**; `_CONTRACT_COLUMNS` / `_CONTRACT_FROM`
  (`:141-151`) drop the `sites` join and `site_active`, gain `site_codes` (§ 5.2); `create_contract`
  (`:468-488`) loses the site lock; `change_contract` (`:491-513`) loses the site branch; `_check_node`
  (`:541-558`) loses the site rule; `_overlaps` (`:272-287`) loses its site list; `renew_contract`
  (`:617-657`) loses the site lock and site; `_sees_whole_site` (`:751-758`) and `_vendor_reach`
  (`:739-748`) take the line sites (§ 5.7); `contract_calls` answers `site_codes` and `warning_sites`
  instead of `site_code`; `_LINE_SELECT` (`:223-228`) drops `s.id AS site_id` (used only by
  `at_contract_site`). Docstrings: the module summary (`:1-15`: "at one site", "node of the
  contract's site", "at the old one's site", "machines of the site"), the ACCESS and LOCK ORDER
  docstring (`:19-102`; § 5.8), `_renewal_links`' (`:318-319`, "contracts of the same site": a reader
  of one reads the other because `read_basic` is global).
- `backend/alerts.py`: `_ALERT_CONTRACT` (`alerts.py:434-438`) without the `sites` join;
  `read_alert_contract` adds `site_codes`; `contract_recipients` (`:494-499`) over the line sites
  (§ 5.6); `people_with_role_at_site` (`:181-186`) becomes `people_with_role_at_sites(cur, site_ids,
  roles, with_email=False)` **(new name)** and `_people_with_role` (`:189-213`) takes a `site_ids`
  list (§ 5.6); the module docstring (`:26-37`).
- `backend/alerts_core.py`: `CONTRACT_AUDIENCE_KEY`'s comment (`alerts_core.py:84-88`); `contract_facts`
  and `contract_text` (`:408-437`) use `site_codes`; `you_get` (`:459-502`) words its contract lines as
  § 5.6.
- `backend/email_core.py`: `contract_ending_email` (`email_core.py:182-197`): subject and the *Sites*
  field from `site_codes` (§ 5.6).
- `backend/task_handlers.py`: `contract_alert`'s docstring (`task_handlers.py:325-330`) only.
- `backend/documents.py`: the contract owner's comment (`documents.py:216-218`) and module docstring
  (`:37-42`); `_REMOVED_CONTRACT_BRANCH` (`:568-575`) without the `sites` join; `_removed_item`'s
  contract branch (`unit` None); `_removed_branches` (`:669-673`): the branch when `has_perm` of
  `contract:read_senior` (§ 5.9).
- `backend/equipment.py`: `list_equipment`'s Contract filter (`equipment.py:667-673`) calls
  `covered_sql(coverage, today)`; the import of `sites_holding` (`:156`) goes; the contracts.py
  bullet of its LOCK ORDER (`:69-81`, § 5.8).

### Frontend (10 files)

- `frontend/src/views/masters/ContractsPanel.vue`: no `addableSites` / `chosenSite`; the global flags
  from the list's answer; the Site filter from `sites`; a **Sites** column and the phone line from
  `site_codes` (§ 5.10); the docstring (`:4-9`: "at one site", "the chosen site's flags").
- `frontend/src/views/contracts/ContractFields.vue`: the Site field and the props `sites`, `siteCode`
  go (`ContractFields.vue:8`, `:19-20`, `:50-58`); the cost note's help "Only the managers of this
  site see this note." (`:172`) → "Only the managers see this note.".
- `frontend/src/views/contracts/ContractRenewDialog.vue`: `blank` without `site_id` (`:31`);
  `renewalNotice` without the site (`:54`); no `:site-code` (`:94`).
- `frontend/src/views/contracts/ContractMachineDialog.vue`: no `:site-id` and no `:empty-text`
  (`:90-91`): the picker's own "No equipment found at your units."; the price help "Only the managers
  see it." (`:108`); the docstring (`:4-5`).
- `frontend/src/views/ContractView.vue`: the header line (`:159`), "Contract not found." (`:140`), no
  "Now at …" line (`:239`), the documents line "Only the managers see these documents and photos."
  (`:266`); the docstring (`:14`, "contract:read_senior at the site").
- `frontend/src/views/contracts/BreakdownCallsCard.vue`: `vendorWarningText` with `warning_sites`
  (`:33`); the docstring (`:11-12`, "the whole site", "at the site").
- `frontend/src/views/equipment/UnderContractCard.vue`: `canRead` and `canEdit` from the global
  `userPermissions` (`:28-29`; § 5.4); the docstring (`:9-10`, "the node's site permissions").
- `frontend/src/utils/contractLabels.js`: `contractBody(form, flags)` without `site_id` (`:61-71`);
  `contractForm` without `site_id` (`:95`); `renewalNotice(renewal, canReadCost)` (`:121`, `:142-145`);
  `vendorWarningText(warning, vendorName, siteCodes)` (`:334-345`); `siteCodesText(codes)` **(new)**.
- `frontend/src/views/settings/RemovedDocuments.vue`: a contract row shows its number alone
  (`RemovedDocuments.vue:213`); the docstring (`:19`).
- `frontend/src/components/EquipmentPicker.vue`: the props `siteId` and `emptyText` (`:17-18`) are
  removed, with the `site_id` parameter (`:39`) and the docstring's sentence (`:6-8`); the empty
  text is the fixed "No equipment found at your units." After S087 no caller passes either
  (`RaiseTicketView.vue:266`, `ReadingsRegister.vue:152`, and `ContractMachineDialog.vue` from this
  step), so they go by the rule of F10.

`TicketContractLine.vue` does not change: it reads no site, and its `canRead` uses the ticket's site
permissions, which hold `contract:read_basic` for every site role (§ 5.4).

### Tests (20 files written, 6 removed)

- `backend/tests/fixtures/migrations_v47.py` **(new)**: the frozen texts of v42–v47 (§ 4.1).
- `backend/tests/test_migration_v50.py` **(new)** (§ 8.1); `test_migration_v42.py` …
  `test_migration_v47.py` (six files) are **removed**: their versions no longer exist in
  `_MIGRATIONS`, and § 8.1 covers what they checked.
- `backend/tests/test_contracts_api.py`, `test_contracts_core.py`, `test_contract_equipment_api.py`,
  `test_contract_card_api.py`, `test_contract_calls_api.py`, `test_contract_renewal_api.py`,
  `test_contract_alerts.py`, `test_alerts_core.py`, `test_email_core.py`, `test_push_api.py`,
  `test_rbac.py`, `test_documents_api.py`, `test_removed_documents_api.py`, `test_equipment_api.py`
  (§ 8.2, § 8.3).
- `frontend/tests/contractLabels.test.js`; `frontend/e2e/contracts.spec.js`,
  `frontend/e2e/notifications.spec.js` (§ 8.4).

### Docs (housekeeping, by the coder)

- `docs/schema/notes.json`: the `contracts` line ("one row per contract at one site (`site_id`, fixed
  after create)" → "one row per contract, company-wide (S087, v50: no `site_id`): its sites are its
  machines' sites"; the index list: `ix_contracts_active_to`, not `ix_contracts_site`); the
  `contract_equipment` line ("a node of the contract's site when added" → "a node of any site, inside
  the adder's units when added (S087)"); the `equipment_documents` line (`notes.json:19`: "a
  contract's only by the site's manager (S083 E2)" → "a contract's only by a manager (S083 E2,
  S087)"). Then `tooling\schema-docs.bat write`, read
  `git diff docs/schema/`; `check` exits 0.
- `docs/Plan.MD` § 2 item 9: "one site per contract" → "one contract may cover machines of several
  sites (S087, 31-10-2026; R02 Q1.5 reversed)"; "managers of the site" → "managers"; "engineers and
  managers of the site" → "engineers and managers"; the S084 line in § 6 (*Contract reminders*):
  "at the contract's site" → "at the sites of the contract's machines".
- `.claude/CLAUDE.md`, each line named:
  - § Yantra Specifics, *Files (S006)*: the contract owner: "read with `contract:read_senior`, written
    with `contract:edit` and `contract:read_senior`, restored and erased by `equipment:purge_documents`
    (held at any site) with `contract:read_senior`, so IT admin sees none" (no "at its site", "there").
  - *RBAC deviation (S011)*: add "The four contract keys are global (S087): a contract has no site."
  - *Notifications (S021)*, the S084 sentence: "to the holders of `contract:read` at the sites of the
    contract's machines (every site when it has none), and email to the holders of
    `contract:read_senior` there with an address"; `alerts.people_with_role_at_site` →
    `alerts.people_with_role_at_sites` in that bullet (twice: "no unit condition" and "the recipient
    query").
  - § SMTW-Review: *Contract fields by key (S080)*: drop "at the contract's site" and "the list filter
    counts only contracts at `sites_holding(cur, "contract:read_basic")`"; *Contract documents* (in
    the S080 point, S083 part): drop "at the contract's site" and "the removed list keeps contract rows
    to the sites where both … are held" → "the removed list shows contract rows to holders of
    `contract:read_senior`"; *Contract reminders (S084)*: "at the sites of the contract's machines";
    *Contract renewal (S085)*: "the in-service machines of the site" → "the machines not scrapped";
    *Breakdown calls (S086)*: "every unit of the contract's site" → "every active unit of each site of
    the contract's machines".
  - § SMTW-Review, the new point of § 8.6.
  - **Version mentions** (`(v46; the To date reminded for …)` in *Notifications*, `(v47)` in
    *Contract renewal (S085)*): **kept as they are**, the least churn and the same rule as S088's
    `(v40; …)`: they name the step's original migration. The bullet **Migrations (S025, S088)**
    becomes **Migrations (S025, S088, S087)** and gains one sentence: "v42–v47 (S079–S085, never
    released) and S087's change were squashed into **v50** (S087, 31-10-2026); a note that names
    v42–v47 names the step's original migration."; its "The old texts live only in
    `backend/tests/fixtures/migrations_v41.py` (frozen; it starts at v20)" becomes "The old texts live
    in `backend/tests/fixtures/migrations_v41.py` (v20–v41) and `backend/tests/fixtures/migrations_v47.py`
    (v42–v47), frozen". § SMTW-Review *Migrations* (which lists S088's squash: "`_MIGRATIONS` starts at
    v41 …") gains "v42–v47 squashed into v50 (S087), their texts in `migrations_v47.py`". `docs/schema/notes.json`'s version tags (`v43`, `v44`, `v46`, `v47`)
    stay under the same rule; only the lines this step rewrites name v50.
- `docs/steps/device-checks.md`: no row (§ 8.5).
- `docs/roadmap/R02-amc-contracts.md`: not edited by the coder; the orchestrator records in R02's log
  that Q1.5 is reversed by S087 (and that D5's and D10's "of the contract's site" no longer hold).

**File count:** 41 code and test files written (11 backend, 10 frontend, 20 test files) and 6 test files removed, 3 docs plus the
generated schema docs. Over the ~25 guide: § 9 Q5 proposes a split line.

## 4. Data model

### 4.1 Migration v50: v42–v47 squashed, with S087's change (KLA, 31-10-2026; § 7 F12)

S088 (coded **before** S087) squashes the released v20–v41 into one entry v41. S087 then replaces
v42–v47 (S079–S085, never released) and its own planned change with **one entry, v50**, that holds
the final R02 schema. `LATEST_VERSION` follows the last entry, so it is 50. **Why 50:** a squashed entry is numbered above the
highest version any database has recorded (SMTW-WebApp-Base § Local DB Migration Pattern › Migration
squashing); dev and test databases hold up to v47; v48 would also qualify, and v50 is the number
KLA named (F12). The runner applies every version not in `db_version` (`local_db.init_db`,
`local_db.py:1412`), so the gap v42–v49 is allowed and the old v42–v47 rows of a dev database stay
as history.

**What v42–v47 did** (`backend/local_db.py`, the six entries before `LATEST_VERSION`):

| Version (step) | Statements |
|---|---|
| v42 (S079) | `CREATE TABLE vendors`; `people`: `vendor_id` (after `employment`), `ix_people_vendor`, `fk_people_vendor`; `chk_people_vendor` |
| v43 (S080) | `CREATE TABLE contracts` (with `site_id`, `ix_contracts_site`, `fk_contracts_site`, `ix_contracts_renewal_of`) |
| v44 (S081) | `CREATE TABLE contract_equipment`; `equipment_events.event` ENUM gains `contract_added`, `contract_removed` |
| v45 (S083) | `equipment_documents`: `contract_id` (after `procedure_id`), `ix_equipment_documents_contract`, `fk_equipment_documents_contract`; `chk_equipment_documents_owner` dropped and added with six owners |
| v46 (S084) | `contracts`: `first_reminder_for`, `second_reminder_for` (after `to_date`) |
| v47 (S085) | `contracts`: `uq_contracts_renewal_of` added, `ix_contracts_renewal_of` dropped |

**v50's statements, in order** (each safe to run twice, so a half-applied v50 re-runs):

1. `CREATE TABLE IF NOT EXISTS vendors (…)`: v42's text.
2. `ALTER TABLE people ADD COLUMN IF NOT EXISTS vendor_id …, ADD KEY IF NOT EXISTS ix_people_vendor
   …, ADD CONSTRAINT fk_people_vendor FOREIGN KEY IF NOT EXISTS …`; 3. `ALTER TABLE people ADD
   CONSTRAINT IF NOT EXISTS chk_people_vendor …`: v42's texts.
4. `CREATE TABLE IF NOT EXISTS contracts (…)` in the **final shape**: v43's columns without
   `site_id`, with `first_reminder_for` and `second_reminder_for` after `to_date` (v46's place);
   keys `ix_contracts_active_to (active, to_date)`, `ix_contracts_vendor`, `UNIQUE KEY
   uq_contracts_renewal_of (renewal_of_id)`; `fk_contracts_vendor`, `fk_contracts_renewal_of`; v43's
   four CHECKs. The column order is v47's less `site_id`, so a converged dev table and a fresh one
   compare equal (§ 8.1).
5. **Convergence of an older `contracts`** (no-ops on a table step 4 created), **seven statements,
   one `ALTER TABLE contracts` each**, as every entry writes them (BR3-02):
   `ALTER TABLE contracts ADD COLUMN IF NOT EXISTS first_reminder_for DATE NULL AFTER to_date, ADD
   COLUMN IF NOT EXISTS second_reminder_for DATE NULL AFTER first_reminder_for` (v46);
   `ADD UNIQUE KEY IF NOT EXISTS uq_contracts_renewal_of (renewal_of_id)`, then `DROP INDEX IF EXISTS
   ix_contracts_renewal_of` (v47's order); `DROP FOREIGN KEY IF EXISTS fk_contracts_site`; `ADD KEY IF
   NOT EXISTS ix_contracts_active_to (active, to_date)`; `DROP INDEX IF EXISTS ix_contracts_site`;
   `DROP COLUMN IF EXISTS site_id`. The site's foreign key goes before its column (a column under a
   foreign key cannot be dropped); `ix_contracts_site` is dropped by name, because dropping only the
   column would leave `(active, to_date)` under that name.
6. `CREATE TABLE IF NOT EXISTS contract_equipment (…)`: v44's text (unchanged since).
7. `ALTER TABLE equipment_events MODIFY event ENUM(…, 'contract_added', 'contract_removed')`: v44's
   text (a re-run is a no-op).
8. `ALTER TABLE equipment_documents ADD COLUMN IF NOT EXISTS contract_id …, ADD KEY IF NOT EXISTS
   ix_equipment_documents_contract …, ADD CONSTRAINT fk_equipment_documents_contract FOREIGN KEY IF
   NOT EXISTS …`; `DROP CONSTRAINT IF EXISTS chk_equipment_documents_owner`; `ADD CONSTRAINT IF NOT
   EXISTS chk_equipment_documents_owner CHECK (… six owners …)`: v45's three texts (drop and add, so
   a five-owner CHECK at v41 becomes the six-owner one).

- **The key `ix_contracts_active_to`** serves the list (`c.active = 1`, the status bounds on
  `to_date`, `ORDER BY c.to_date`) and the scan (`active = 1 AND to_date BETWEEN …`,
  `alerts.contract_scan_candidates`). Tens of rows: one key is enough.
- **The old texts** of v42–v47 move, frozen and never edited, to
  `backend/tests/fixtures/migrations_v47.py` **(new)** (`MIGRATIONS_V42_V47`, the six tuples as they
  stand today, with their comments), as S088's `fixtures/migrations_v41.py` holds v20–v41. The upgrade tests build v47's shape from it (§ 8.1).
- **Behaviour of `DROP FOREIGN KEY IF EXISTS`, `DROP INDEX IF EXISTS` and `DROP COLUMN IF EXISTS`**
  on a table without them: a Note (1091), no error. Checked on MariaDB 11.4 in brief review round 3.
  `DROP INDEX IF EXISTS` is v47's form and `DROP CONSTRAINT IF EXISTS` v45's; `DROP FOREIGN KEY IF
  EXISTS` and `DROP COLUMN IF EXISTS` are in neither `_MIGRATIONS` nor `migrations_v41.py`;
  `DROP COLUMN IF EXISTS` was last used in v1–v13 (git history). § 8.1's tests keep the record.

### 4.2 Production, dev databases and preconditions

v50 must be right on three shapes:

| Shape | Who has it | What v50 does |
|---|---|---|
| (a) fresh after v41 | a new install, the e2e databases (rebuilt every run), the migration tests | steps 1–8 create everything; step 5 is a no-op |
| (b) **production at v41** (the real target) | production: last release v0.1.14 (`e77d635`), schema at v41 | the same as (a): no table or column of v50 exists there; `people` gains `vendor_id` (NULL on every row; a NULL foreign key is not checked; `chk_people_vendor` holds for NULL), `equipment_documents` gains `contract_id` (NULL) and the six-owner CHECK, which every row meets (each has one of the five owners) |
| (c) **dev and test at v47** (any of v42–v47) | `vel_yantra_master`, the kept worker databases `vel_yantra_test_<run>_<worker>` | every `IF NOT EXISTS` piece is a no-op; step 5 converges `contracts`: drops `fk_contracts_site`, `ix_contracts_site`, `site_id` (with their values), adds `ix_contracts_active_to`; a database stopped at v43–v45 also gains the v46 columns, and one stopped at v43–v46 v47's key |

- **Converge, not refuse** (§ 7 F12): the three drops cost three idempotent statements, and the kept
  worker databases are reused between runs, so a refusal ("drop and rebuild") would stop every
  developer's test run once. Rejected: a `_PRECONDITIONS` refusal of a database that holds
  `contracts.site_id`.
- **No `_PRECONDITIONS` entry:** production (b) holds no row v50 converts; on (c) dropping `site_id`
  with its values is the decision (F1, F3: the site is no longer a fact of the contract). This also
  holds if a release had gone out with v42–v47: v50 would converge it the same way.
- **Rollback:** the release to roll back to is v0.1.14 (v41), which never reads `vendors`,
  `contracts`, `contract_equipment`, `people.vendor_id` or `equipment_documents.contract_id`. On it, a
  `PUT {employment: "direct"}` of a linked person breaks `chk_people_vendor` (v42's stated rollback
  note): unlink such people before a rollback.
- **Depends on S088:** v50 sits after S088's v41 in `_MIGRATIONS`; S087's coder starts from S088's
  committed code (§ 9 A5).

### 4.3 What is computed, never stored

A contract's sites (`site_codes`), the list's Site filter, the reminder recipients, the calls'
`complete` and the vendor warning's sites (§ 5).

## 5. Rules

### 5.1 Access: every contract check becomes global

The four keys leave `SITE_SCOPED`. `has_perm_at` and `require_perm_at` assert their key is in
`SITE_SCOPED` (`auth_utils.py:432-436`), so every contract call of them must change, or a test fails
on the assertion. Each place:

| Place (contracts.py unless named) | Today | After S087 |
|---|---|---|
| `_SiteFlags.at(site_id)` (`:176-193`) | `has_perm_at` per site | `_flags()` **(new)**: `has_perm` of `EDIT`, `READ_CALLOUT`, `READ_COST`, once per request; the same five flags |
| `_detail` overlaps (`:295`) | `sites_holding(cur, READ_BASIC)` | no site list (§ 5.3) |
| `_answer` (`:338-341`) | `_SiteFlags().at(row["site_id"])` | `_flags()` |
| `_drop_gated(clean, site_id, fields)` (`:344-349`) | `has_perm_at(key, site_id)` | `_drop_gated(clean, fields)`, `has_perm(key)` |
| `list_contracts` (`:378-416`) | `sites_holding`, per-site flags | § 5.10 |
| `get_contract` (`:419-426`) | 404 without `read_basic` at the site | 404 only when missing (the decorator checks `read_basic`) |
| `contracts_for_equipment` (`:439-465`) | keeps contracts at sites where `read_basic` is held | keeps every contract found; `_flags()` |
| `create_contract` (`:468-488`) | site lock, `require_perm_at(EDIT, site)` | no site; the decorator's `require_perm(EDIT)` (§ 5.8) |
| `change_contract` (`:491-513`) | 404 / 403 at the site; `SITE_KEPT` | 404 when missing; no site branch |
| `_lock_contract(cur, id, key)` (`:520-528`) | 404 without `read_basic` at the site, `require_perm_at(key)` | 404 when missing or `has_perm(READ_BASIC)` false; `check_perm(key)` (403, `FORBIDDEN_TEXT`) |
| `change_price` (`:590-591`) | `require_perm_at(READ_COST, site)` | `check_perm(READ_COST)` |
| `renew_contract` (`:626-646`) | site, `has_perm_at(READ_CALLOUT, site)` | `has_perm(READ_CALLOUT)` (§ 5.5) |
| `contract_calls` (`:789`) | 404 without `read_basic` at the site | 404 only when missing |
| `_contract_access(row, key)` (`:819-826`) | `has_perm_at` / `require_perm_at` at the site | 404 when missing or no `read_basic`; `check_perm(READ_COST)`; `check_perm(key)` |
| `_contract_site(cur, id)` (`:829-831`) | `SELECT id, site_id …` | `SELECT id FROM contracts …`, renamed `_contract_id_row` **(new)** |
| `lock_contract_for_change` (`:851-856`) | `require_perm_at(READ_COST, site)` | `check_perm(READ_COST)` |
| `equipment.list_equipment` (`equipment.py:667-673`) | `sites_holding(cur, "contract:read_basic")` | no check: `covered_sql(coverage, today)` (§ 5.4) |
| `documents._removed_branches` (`documents.py:669-673`) | sites with both keys | § 5.9 |

- **The `has_perm(READ_BASIC)` 404 in `_lock_contract` and `_contract_access`: kept.** Today it
  cannot fire: every caller has passed `require_perm(EDIT)` or `documents._owner_key`, and every
  holder of `edit`, `read_senior` or `purge_documents` holds `read_basic` (`("*",)`). It stays as
  the fail-closed habit: one line, and a later caller with a key whose holders lack `read_basic` (or
  a narrowed `read_basic`) gets a 404, not a contract it may not read. The tests do not try to reach it.
- **The 403 text** for a contract check becomes `FORBIDDEN_TEXT` ("You don't have permission for
  this. Ask your engineer or IT.", `auth_utils.py:64`), as every global key's; "You can't do this at
  SMTW" no longer comes from a contract route.
- **Holders do not change** (`config_rbac.py:163-166`): `read_basic` every role, `read` the engineer
  (so the manager), `read_senior` the manager, `edit` the engineer (so the manager) and IT admin.
  `test_role_matrix` is unchanged.
- **What it means per role.** An engineer of SMTW now reads the call-out number of, and edits, a
  contract whose machines are all at BRICKS. A manager of SMTW reads every contract's prices, cost
  note and documents (KLA accepted this, decision 1). **IT admin:** `it_admin` is a token role
  (`config_rbac.TOKEN_ROLES`), which already held its keys at every site; it still edits every
  contract and reads neither the call-out number nor the cost note nor a price nor a document. No
  change for IT admin.
- **Fail-closed, unchanged:** no identity → 401 from `require_auth`; a login with only
  `maintenance_team` holds no `("*",)` key (`config_rbac.LOGIN_ROLE` is not in `ROLES`) → 403
  (`test_a_login_without_a_site_role_is_refused` stays). An unknown key grants nobody. Admin bypasses
  in `has_perm`.

### 5.2 A contract's sites

- **The path:** a line's node → its root equipment's unit → the unit's site, as `NODE_JOINS`
  (`COALESCE(gp.unit_id, p.unit_id, e.unit_id)`). One copy in `contracts_core`:
  `LINE_SITE_JOINS` **(new)** = `" JOIN equipment e ON e.id = ce.equipment_id LEFT JOIN equipment p
  ON p.id = e.parent_id LEFT JOIN equipment gp ON gp.id = p.parent_id JOIN units u ON u.id =
  COALESCE(gp.unit_id, p.unit_id, e.unit_id) JOIN sites s ON s.id = u.site_id"`, and
  `LINE_SITES_SQL` **(new)** = `"SELECT DISTINCT s.id, s.code FROM contract_equipment ce" +
  LINE_SITE_JOINS + " WHERE ce.contract_id = %s ORDER BY s.code"`. `contracts_core` already holds SQL
  pieces (`covered_sql`); `alerts.py` never imports `contracts.py` (`alerts.py:37`) but may import
  the pure `contracts_core` (`alerts_core.py` already does, `alerts_core.py:21`; a new import in
  `alerts.py`), so both modules share one copy. Not `NODE_JOINS` itself: it also joins
  `equipment_classes c`, whose alias meets `contracts c`.
- **Current, not at add:** a machine moved to BRICKS counts at BRICKS from the move on. Every line
  counts, a scrapped machine's too (its line stays, S081).
- **In the answers:** `_CONTRACT_FROM` gains `LEFT JOIN (SELECT ce.contract_id, GROUP_CONCAT(DISTINCT
  s.code ORDER BY s.code SEPARATOR ',') AS site_codes FROM contract_equipment ce` + `LINE_SITE_JOINS`
  + ` GROUP BY ce.contract_id) cs ON cs.contract_id = c.id`; `_contract_out` sends `site_codes` as a
  list (`[]` for no line). A site code holds no comma (`masters_core.SITE_CODE_RE`,
  `masters_core.py:14`). The answer has no `site_id` and no `site_code` any more.
- **Each line** keeps `site_code` and `full_path` (which starts with the site code,
  `equipment.node_path`); `at_contract_site` goes (`contracts.py:262`).

### 5.3 Overlaps (S081 § 5.6)

`_overlaps(cur, contract, lines)`: the `c2.site_id IN (…)` filter goes (`contracts.py:278`). Every
reader holds `read_basic` at the company level, so every other active contract of the same type on
the node, its ancestor or its part shows.

### 5.4 Machines, the card and the ticket line

- **Add machine** (`_check_node`, `contracts.py:541-558`): rules 2 (inside the adder's units,
  `accessible_unit_ids(cur)`, i.e. `equipment:read`; IT admin every unit by
  `equipment:read_all_units`) and 3 (not scrapped, 409) stay; rule 4 (the contract's site,
  `:555-558`) goes. The node read keeps `root_unit_id` only.
- **Remove a machine** and **change a price**: no unit check, as S081 (§ 9 Q4).
- **The picker** in `ContractMachineDialog.vue` passes no `siteId`; it searches the adder's units,
  so an engineer of SMTW finds no BRICKS machine and sees "No equipment found at your units."; a
  manager of both sites finds both.
- **The Under contract card** (`/for-equipment/<node_id>`): every contract with a line on the node
  or its ancestors (§ 5.1). In `UnderContractCard.vue`, `canRead` and `canEdit` read the global
  `userPermissions` (`frontend/src/stores/auth`), as `EquipmentView.vue:58` does for the Contract
  filter: the keys are no longer the node site's. (An engineer of VEL who is an operator at SMTW
  sees "No contract on this machine." on an SMTW machine, and may add it: they read it, so
  `_check_node` passes.)
- **The ticket line** (`TicketContractLine.vue`) reads no site; unchanged.
- **The equipment list's Contract filter:** `covered_sql(coverage, today)`: the `EXISTS` without the
  `ct.site_id IN`; the `"0 = 1"` / `"1 = 1"` branch for "no site" goes. No key check: the caller has
  passed `require_perm("equipment:read")`, and every holder of a site role holds `contract:read_basic`
  (`("*",)`), as IT admin's token does (`compute_permissions`).

### 5.5 Create, change and renewal

- **Create:** `validate_contract` has no `site_id` field; `REQUIRED` is `("vendor_id",
  "contract_type", "title", "from_date", "to_date")`. A `site_id` sent is an unknown field and is
  **ignored**, on `POST` and `PUT` (`validate_contract` already ignores unknown fields,
  `contracts_core.py:148-152`). No 400 (§ 7 F5).
- **Change:** the `SITE_KEPT` branch (`contracts.py:504-506`) goes. Any other field as S080.
- **Renewal** (`renew_contract`): `clean_body(validate_contract, creating=True)`; `validate_renewal`
  is removed (its one job was dropping `site_id`). Refusals: inactive contract 409, already renewed
  409, vendor 400, the unique key 409 (S085 § 5.5); **"SMTW is inactive …" goes** (no site). The
  insert has no `site_id`; `renewal_of_id` as S085. The call-out number copied for a renewer without
  `contract:read` (S085 § 5.4) now asks `has_perm(READ_CALLOUT)`.
- **Lines copied:** every line whose node is not scrapped, at any site, also one in an inactive unit
  or at an inactive site (§ 7 F6). `renewal_lines(machines)` → `(copied, skipped)`; `skipped` holds
  only `"scrapped"`; the lines need `equipment_id`, `code`, `lifecycle`. The renewer's units are not
  asked (S085 § 5.3, unchanged).
- **`can_renew`** = `can_edit`, the contract active, `renewed_by` `null` (no `site_active`).
- **Texts:** `renewalNotice` says "Prices start empty: the managers enter them on the new contract."
  (no site); "Not copied: CMP004 (scrapped)."

### 5.6 Reminders (S084)

- **Recipients** (`alerts.contract_recipients(cur, contract, channel)`): the holders of the channel's
  key (`CONTRACT_AUDIENCE_KEY`: push `contract:read`, email `contract:read_senior` with an address)
  **at each site of the contract's machines** (`LINE_SITES_SQL`), in **one query**:
  `people_with_role_at_sites(cur, site_ids, roles, with_email)` **(new name** of
  `people_with_role_at_site`), over `_people_with_role` with a `site_ids` list (`ms.site_id IN (…)`,
  `SELECT DISTINCT p.id … ORDER BY p.id`), so each person comes once. `people_at_unit` passes its one
  site as `[site_id]`. **A contract with no line:** the same call with the ids of every site
  (`SELECT id FROM sites`, inactive sites too: the simplest rule, and a membership at an inactive
  site is rare), so a reminder is never lost (§ 9 Q1, Q2: KLA to decide). `site_ids` empty (no site
  at all) → `[]`, no `IN ()`.
- **Why by the machines' sites** (recommended): the people who work with the machines get the
  reminder; an SSVT engineer is not reminded about a SMTW compressor AMC. Every recipient may open
  the contract (`read_basic` is global and held by every site role).
- **The texts** (`contract_facts`, `contract_text`, `contract_ending_email`): `site_codes` (sorted)
  replaces `site_code`. Push title "Contract ends in 60 days · BRICKS, SMTW"; no line → "Contract
  ends in 60 days". Email subject "Contract ends on 31-03-2027: VP Power UPS AMC 2026–27 (BRICKS,
  SMTW)", no brackets with no line; the field *Site* becomes *Sites* with the codes, left out with no
  line. Never a price, cost note or call-out number (unchanged); the payload carries no person and no
  address (unchanged).
- ***What you will get*** (`you_get`, `alerts_core.py:480-502`): "Contracts ending at SMTW" becomes
  "Contracts ending for machines at SMTW"; ", by email" as before. One line per membership, as S084.
- **The scan** (`contract_reminder_scan`) and the markers (v46) do not change.

### 5.7 Breakdown calls (S086)

- **`complete`** (`_sees_whole_site` → `_sees_covered_sites(cur, site_ids)` **(new)**): `True` when
  `accessible_unit_ids(cur, "ticket:read")` is `None`, or holds every active unit of every site in
  the contract's line sites (`LINE_SITES_SQL`). No line → no calls (`_call_rows` returns `[]`) and
  `complete` `True` (an empty set of units). Rejected: the units of the covered machines only (§ 7 F4).
- **The vendor warning** (`_vendor_reach(cur, vendor_id, site_ids)`): the active Team records linked
  to the vendor (as today), and per line site the count of them whose role there is in
  `ASSIGNABLE_ROLES`. `vendor_warning(linked_count, assignable_by_site)` → `None`, `("no_linked",
  [])` or `("no_assignable", codes)` with the codes of the sites where the count is 0, sorted. No
  line → only `no_linked` can show.
- **The answer:** `site_code` goes; `warning` stays `null` / `"no_linked"` / `"no_assignable"`;
  `warning_sites` **(new)**: the codes for `no_assignable`, else `[]`. Text: "No Team record of VP
  Power can be assigned at BRICKS, SMTW-KP. Give one a Technician role there in Masters › Team."
- The rows' ticket predicate, the figures (`tickets_core.ticket_times`) and "no hidden count" are
  unchanged (S086 § 5.5).

### 5.8 Locks

The database runs REPEATABLE READ. Changes to the LOCK ORDER note (`contracts.py:41-102`):

- **Create:** the vendor LOCK IN SHARE MODE (`masters.check_active_vendor`: missing or inactive 400)
  → the insert (its shared foreign-key lock on the vendor, held) → the answer. No site lock, and the
  key check is the decorator's, before the transaction.
- **Renew:** the old contracts row FOR UPDATE, first (`_lock_contract`: 404, `contract:edit` 403) →
  plain: active 409 → plain: a renewal of it 409 → `_drop_gated`, the call-out number, the rules →
  the vendor LOCK IN SHARE MODE (400) → the insert (shared foreign-key locks on the vendor, held, and
  the old contract, held exclusive) → the lines sorted by `equipment_id`; per line the node (1) LOCK
  IN SHARE MODE, in id order → per copied line the insert and the history line → the answer.
- **No deadlock cycle:** the bullet "The site row: masters.py's site update locks site rows … it may
  wait for a create's shared lock" (`contracts.py:98-100`) goes: no contract write locks a site row.
  "Two contract writes: creates share the site and vendor locks" (`:101`) → "creates share the vendor
  lock". "The renewal (S085), after the old contract, waits only on the site, the vendor and nodes
  (1)" (`:80-81`) → "only on the vendor and nodes (1)".
- **Add a machine:** unchanged order; "plain: the node's site and units through NODE_JOINS (400)"
  (`:53`) → "plain: the node's units (400)".
- **`equipment.py`'s contracts.py bullet** (`equipment.py:69-81`): "a contract create takes the site
  and the vendor LOCK IN SHARE MODE" → "takes the vendor LOCK IN SHARE MODE"; "then the site, the
  vendor and the covered nodes (1)" → "then the vendor and the covered nodes (1)".
- **The reads** added (`LINE_SITES_SQL`, the `site_codes` subquery) are plain, no lock. The reminder
  task reads them plain, as it reads the contract (`alerts.read_alert_contract`).

### 5.9 Documents (S083)

- **Read, add, retitle, remove:** `contract:read_senior` held (anywhere) and, to write,
  `contract:edit`; 404 for a missing contract. Unchanged otherwise.
- **Restore and purge:** `equipment:purge_documents` held at any site (`check_perm`, as
  `documents._owner_key` already checks first) and `contract:read_senior`. A site-scoped key checked
  by the union, as the model owner does (a site-less record). Holders: managers (both keys); IT admin
  holds purge but not `read_senior`, so still none (§ 9 Q3).
- **The removed list:** the contract branch is added when `has_perm("contract:read_senior")`; the
  route already needs `equipment:purge_documents` somewhere. No site scope.
- **The Site column:** a contract document's row has `unit` `None` (as a model's); the screen shows
  "Contract <title>" and its number alone (`RemovedDocuments.vue:213`). Rejected: the machines'
  sites (§ 7 F8).

### 5.10 Masters › Contracts

- **The list's answer** (`GET /api/contracts`): `items`, `total`, `sites` (every site, ordered by
  code: `{id, code, name, active}`, for the filter), `can_add` (`has_perm(EDIT)`),
  `can_read_callout`, `can_read_cost` **(new top-level flags)**; the per-site flags go. Each item
  carries `site_codes` and S080's per-item flags (from `_flags()`).
- **The Site filter** (`site_id`): the contracts with at least one line at that site:
  `EXISTS (SELECT 1 FROM contract_equipment ce` + `LINE_SITE_JOINS` + ` WHERE ce.contract_id = c.id
  AND s.id = %s)`. An unknown site → an empty list (no 400 beyond `int_arg`'s). A contract with no
  line shows only under *All sites*. The dropdown shows inactive sites with " (inactive)".
- **The filter's opening value: *All sites*** (recommended; § 9 Q6, KLA to decide at gate A). Today a
  one-site engineer's list holds only that site's contracts; after S087 it opens on every contract.
  Recommended: keep *All sites* for everyone (one rule, no per-user state, a contract with no machine
  is never hidden by default, the user's site is one tap away; tens of contracts with a *Sites*
  column stay readable). Alternative: preselect the user's site when they hold a membership at
  exactly one site (a contract with no machine, or with machines elsewhere, is then hidden until the
  filter is cleared).
- **The table:** the *Site* column becomes *Sites*: `siteCodesText(site_codes)` **(new)**, "BRICKS,
  SMTW", or "—" for none. The phone line: "AMC · VP Power · BRICKS, SMTW" (the site part left out
  with none).
- **Add contract** shows when `can_add`; the dialog's first row is *Type* alone (no Site); the gated
  fields follow the top-level flags (`contractBody(form, flags)`). The cost note's help reads "Only
  the managers see this note." (`ContractFields.vue:172`).
- **The contract page:** "VP Power · BRICKS, SMTW" under the title; "VP Power" alone with no line.
  "Contract not found." (no "or not at your sites": the 404 now means missing).

### 5.11 The database down

Every route goes through `get_db()`: 503 (§ Yantra Specifics, *DB may not exist*). No task added.

## 6. API changes

| Route | Change |
|---|---|
| `GET /api/contracts` | `site_id` filters by the machines' sites (§ 5.10); `sites` without flags; top-level `can_add`, `can_read_callout`, `can_read_cost`; items without `site_id`, `site_code`, with `site_codes` |
| `GET /api/contracts/<id>` | no `site_id`, `site_code`; `site_codes`; lines without `at_contract_site`; 404 only when missing |
| `POST /api/contracts`, `PUT /api/contracts/<id>` | no `site_id` field (ignored when sent); 403 text `FORBIDDEN_TEXT` |
| `POST /api/contracts/<id>/equipment` | a node of any site inside the adder's units |
| `POST /api/contracts/<id>/renew` | no site refusal; `skipped` only "scrapped" |
| `GET /api/contracts/for-equipment/<node_id>` | every contract on the node (no site filter); items unchanged (`_CARD_KEYS`) |
| `GET /api/contracts/<id>/calls` | no `site_code`; `warning_sites`; `complete` over the line sites |
| `GET /api/equipment/removed-documents` | contract rows to `read_senior` holders; their `unit` `null` |

No new route, no new key. The stale-bundle check (CLAUDE-COMMON) reloads an old tab, whose `site_id`
the server ignores meanwhile.

## 7. Design decisions

- **F1. Company-wide keys (KLA, 31-10-2026, decision 1).** The four contract keys leave
  `SITE_SCOPED` and are checked by the union. A holder of `contract:read` anywhere reads every
  call-out number; `contract:read_senior` anywhere every price, cost note and document; KLA accepted
  that a VEL manager sees SMTW prices. **Rejected:** (a) per machine's site: a contract visible where
  the key is held at a site of any of its machines, its lines and prices filtered per site (a
  contract total that differs per reader, a cost note that covers several sites, more code in every
  route); (b) an owner site plus machines from any site (the keys still at one site, so a SMTW
  manager decides on BRICKS machines while the BRICKS manager does not see the price).
- **F2. A new step after S086 (KLA, 31-10-2026, decision 2)**, built on S080–S086 (committed
  31-10-2026); not a rework of their briefs. The migrations are squashed into v50 (F12).
- **F3. The sites are derived from the lines, never stored** (§ 5.2). One fact (where a machine
  stands) in one place (the unit). Rejected: a `contract_sites` table (a second fact to keep in step
  with moves).
- **F4. `complete` over every active unit of each line site** (§ 5.7), the old rule widened from one
  site to several. Rejected: only the units of the covered machines (a ticket's own unit may differ
  from its machine's current unit, S086's predicate; a site-wide rule keeps "N of M" safe).
- **F5. A `site_id` sent is ignored** (§ 5.5), as every unknown field. Rejected: 400 (an open tab of
  the old bundle would fail its save until reloaded; the field does nothing).
- **F6. A renewal copies every line not scrapped** (§ 5.5), also at an inactive unit or site: the
  lines are the agreed scope, and the editor removes one on the new page. Rejected: skip a line at an
  inactive unit or site with a reason (a third skip rule for a rare case; an inactive unit's machine
  still exists and may still be serviced).
- **F7. The Site filter means "has a machine at that site"** (§ 5.10). Rejected: drop the filter
  (four sites' contracts in one list; a site's engineer wants theirs).
- **F8. A contract document's removed row shows no site** (§ 5.9), as a model's. Rejected: the
  machines' sites (a join for one column; the number and title name the contract).
- **F9. The reminder and email texts name the machines' sites** (§ 5.6). Rejected: no site (the
  reader of a push does not know which plant it is about).
- **F10. Code with no caller after S087 is removed:** `sites_holding`, `validate_renewal`, and
  `EquipmentPicker`'s `siteId` and `emptyText` props (no dead code; one rule for all four).
  Rejected: keep them for a later step (none is planned; a screen that needs a site filter adds it
  back with its own reason).
- **F11. The card's checks read the global permissions** (§ 5.4), as the keys are global.
- **F12. v42–v47 and S087's change are squashed into one migration v50 (KLA, 31-10-2026: "the rest
  as v48 or v50").** S088 squashes the released v20–v41 into v41 first; v42–v47 were never
  released, so production runs only v50. Numbered above every recorded version (dev and test hold
  v47); v48 would also be above it, v50 is the number KLA named and marks the squash. Dev and test
  databases **converge** (step 5 of § 4.1: three idempotent drops of the site, plus the v46/v47
  pieces for an older shape), because the kept worker databases are reused between runs. Rejected:
  (a) append v48 to v42–v47 (KLA chose the squash: one entry for a release that ships all of R02);
  (b) a precondition that refuses a database holding `contracts.site_id` and asks to drop and
  rebuild it (every developer's test run stops once, to save three statements).

## 8. Tests and acceptance

### 8.1 Migration (`backend/tests/test_migration_v50.py`, new)

Built on the upgrade database and S088's helpers: `tests/migration_helpers.py` (`UPGRADE_CONFIG`,
`_recreate`, `_run`, `_migrate`, `_rows`, `_schema`, `_versions`, and `SQUASHED`, the v41 entry,
imported as `test_migration_v36.py` and the squash test do) and `tests/test_migration_v36.py`
(`_keys`, `_foreign_keys`). `V50` = `_MIGRATIONS` (v41 and v50). **The v47 shape** is built in this
order: `_recreate()`, `_migrate(SQUASHED)`, then `_migrate(MIGRATIONS_V42_V47)` (or one list
`[*SQUASHED, *MIGRATIONS_V42_V47]`); never the v42–v47 fixture on an empty database. S088's one-call
rule is about its own fixture; S087's holds no v41, and `_v41_squash_check` is keyed on 41 only, so
it is not consulted once 41 is recorded (`init_db`, `local_db.py:1412-1416`).
The schema comparison reads `information_schema` (columns with their order and types, keys, foreign
keys, CHECKs), as `_schema()` does.
- `test_a_fresh_database_gets_v50` (the fresh path, (a)): `contracts` has no `site_id`; `_keys` has
  `ix_contracts_active_to`, `uq_contracts_renewal_of`, not `ix_contracts_site` or
  `ix_contracts_renewal_of`; `_foreign_keys` has `fk_contracts_vendor`, `fk_contracts_renewal_of`,
  not `fk_contracts_site`; `vendors`, `contract_equipment`, `people.vendor_id`,
  `equipment_documents.contract_id` and the six-owner CHECK exist; `equipment_events.event` holds
  `contract_added`, `contract_removed`.
- `test_production_at_v41_gets_the_fresh_schema` (the production path, (b)): a v41 database with a
  site, a person and a node document (five-owner CHECK) runs v50; `_schema()` equals the fresh
  build's; the rows kept, `people.vendor_id` and `equipment_documents.contract_id` NULL.
- `test_dev_at_v47_converges` (the dev path, (c)): a v47 database built from the fixture, with two
  sites, a vendor linked to a contractor, two contracts (one at each site), a line each, a renewal, a
  reminder marker and a contract document, runs v50; `_schema()` equals the fresh build's; every row
  kept, every column but `site_id` unchanged.
- `test_dev_at_v43_converges`: a database stopped at v43 (fixture's v42–v43) runs v50 and equals the
  fresh build (the v46 columns, v47's key added).
- `test_a_rerun_changes_nothing`: `_schema()` equal after v50's statements run again on each of the
  three paths' results.
- **Moved from the removed files, run on the fresh build** (BR3-01; S088 § 7 D6 keeps constraint tests
  on a squashed entry). A helper `_add_contract` **(new here)** without `site_id` replaces
  `test_migration_v43.py`'s, which inserts one:
  - from `test_migration_v42.py`: `test_an_unknown_vendor_is_refused` (`fk_people_vendor`),
    `test_the_name_is_unique_in_any_case` (`uq_vendors_name`, case-insensitive), the
    `chk_people_vendor` refusal;
  - from `test_migration_v43.py`: the `chk_contracts_*` refusals and boundaries, the unknown vendor
    (`fk_contracts_vendor`), one contract number used twice;
  - from `test_migration_v44.py`: `test_a_node_twice_and_unknown_rows_are_refused`
    (`uq_contract_equipment`, the two foreign keys), `test_the_new_history_kinds_are_stored` (a row
    with each new ENUM value), `chk_contract_equipment_price`;
  - from `test_migration_v45.py`: the owner CHECK refusals;
  - from `test_migration_v47.py`: `test_a_second_renewal_of_one_contract_is_refused`,
    `test_many_contracts_renew_nothing` (many NULLs pass the unique key).
- `test_a_half_applied_v50_converges` **(new)**, on the pattern of
  `test_migration_squash_v41.py::test_a_half_applied_v41_re_runs` (delete the `db_version` row, run
  again, compare `_schema()`), plus the CHECK dropped by hand as the old v45 test did:
  v50 applied; the owner CHECK dropped by hand and the `db_version` row 50 deleted; v50 run again:
  `_schema()` equals the fresh build's, and the CHECK clause names `contract_id`. This covers the
  window between step 8's drop and add (and, by the same re-run, a stop inside step 5), which
  `test_a_rerun_changes_nothing` on a complete result does not. It replaces
  `test_a_half_applied_v42_adds_the_check` and `test_a_half_applied_v45_adds_the_owner_check_again`.
- **Schema docs:** `tooling\schema-docs.bat write`, then `check` exits 0; `git diff
  docs/schema/schema.json` shows only: `"migration": 47` → `50` (`schema.json:3`, and
  `schema-data.js:4`), and `contracts` without `site_id`, `fk_contracts_site` and
  `ix_contracts_site`, with `ix_contracts_active_to` (the rest equal to the v47 shape).
- **Removed:** `test_migration_v42.py`, `test_migration_v43.py`, `test_migration_v44.py`,
  `test_migration_v45.py`, `test_migration_v46.py`, `test_migration_v47.py` (they slice
  `_MIGRATIONS` by v42–v47, which no longer exist; `test_migration_v46.py` and `_v47.py` import
  helpers from `_v43.py`, so all six go together).

### 8.2 Backend, new

- `test_contracts_core.py`: `TestCoveredSql::test_under_and_not_under` rewritten for
  `covered_sql(coverage, today)` (no site parameter, no `IN`);
  `test_renewal_lines` (scrapped only; a line at another site copied); `test_vendor_warning_per_site`
  (no linked; one site with 0 → its code; all > 0 → `None`; no site → only `no_linked`);
  `test_line_sites_sql_names_no_classes_alias` (the string has no " c " alias).
- `test_contracts_api.py`: `test_a_contract_with_machines_of_two_sites` (the manager of both adds an
  SMTW and a BRICKS machine; the detail's `site_codes` `["BRICKS", "SMTW"]`; the list item too);
  `test_the_site_filter_follows_the_machines` (a contract with an SMTW line under `site_id` SMTW and
  not under BRICKS; one with no line only unfiltered); `test_an_engineer_of_one_site_reads_and_edits_every_contract`
  (engineer of B: the detail of a contract with only A machines, its `callout_number`, a `PUT` 200);
  `test_a_manager_of_one_site_reads_every_price` (`price_total`, `cost_note` of an A-only contract);
  `test_a_site_id_sent_is_ignored` (`POST` and `PUT` with `site_id`: 201 / 200, no error);
  `test_the_list_flags_are_global` (top-level `can_add`, `can_read_callout`, `can_read_cost` per
  role; `sites` every site).
- `test_contract_equipment_api.py`: `test_a_machine_of_another_site_is_added`; `test_a_node_outside_the_adders_units_is_refused`
  (engineer of A, node of B: 400 "Choose a machine.").
- `test_contract_alerts.py`: `test_push_to_the_holders_at_each_machine_site` (lines at A and B: the
  engineers and managers of both, each once; not those of a third site);
  `test_email_to_the_managers_at_each_machine_site`; `test_no_line_reaches_every_site`;
  `test_the_texts_name_the_machine_sites`.
- `test_contract_calls_api.py`: `test_complete_needs_every_site_of_the_lines` (a manager of A only,
  lines at A and B → `complete` false, `used` null; a manager of both → true);
  `test_warning_names_the_sites_without_an_assignable_person`.
- `test_contract_card_api.py`: `test_a_contract_with_machines_elsewhere_shows_on_this_machine`.
- `test_rbac.py`: in `test_contract_keys`, the four keys `isdisjoint(SITE_SCOPED)`.
- `test_documents_api.py` (`TestContractDocuments`): `test_a_manager_of_another_site_reads_them`.
- `test_removed_documents_api.py` (`TestContractRows`): `test_a_manager_of_any_site_sees_and_restores_them`.

### 8.3 Existing tests that break (by file and test)

Helpers that only *send* `site_id` keep working (ignored, § 5.5); the coder drops it from them for
clarity: `body` (`test_contracts_api.py:41`), `add_contract` (`test_contract_calls_api.py:60`,
`test_contract_card_api.py:59`), the contract fixture of `test_contract_alerts.py:56` and `:214`. Tests
that assert a site rule, a site field or a site text break:
- `test_contracts_api.py`: `TestCreate::test_an_engineer_of_a_creating_at_b_is_refused_naming_b`,
  `test_an_unknown_or_inactive_site_is_refused` (removed); `TestChange::test_the_site_is_kept`
  (→ `test_a_site_id_sent_is_ignored`), `test_another_sites_engineer` (flips: 200);
  `TestRead::test_the_list_holds_only_the_sites_held` (flips), `test_filters`,
  `test_status_filters_and_order`, `test_total_and_the_cap` (their `site_id=` base: give the
  contracts a line, or drop the filter), `test_sites_and_their_flags_per_role` (top-level flags),
  `test_the_detail` (no `site_code`; another site's reader 200), `test_the_document_flags_follow_the_keys`.
- `test_contracts_core.py`: `test_every_required_field_missing_on_a_post_says_what_to_do` (no "Choose
  a site."), `test_ids_are_whole_numbers` (no `site_id`), `TestCoveredSql::test_under_and_not_under`,
  `TestCoveredSql::test_no_site` (`:349-351`, removed with the `"0 = 1"` / `"1 = 1"` branch),
  `test_renewal_lines`, `test_validate_renewal` (removed), `test_the_messages`
  (`renew_site_inactive` gone).
- `test_contract_equipment_api.py`: `test_engineer_adds_a_machine_and_its_history_shows_it` (if it
  checks `at_contract_site`), `test_a_node_of_another_site_names_the_contract_s_site` (→ added),
  `test_a_moved_machine_is_marked` (no `at_contract_site`; `site_code` of the line),
  `test_overlaps_at_a_site_the_reader_does_not_hold_stay_hidden` (flips: shown),
  `test_an_engineer_of_another_site` (`:186-192`; new outcomes: the stranger, an engineer of B only,
  gets 400 `CHOOSE_MACHINE` for the A machine, outside their units, no longer 404; the test's local
  `operator_here`, an engineer of B and operator at A, gets 201, no longer 403: edit is global and
  the node is inside their units),
  `test_without_the_cost_key_is_403_naming_the_site`
  (`FORBIDDEN_TEXT`), `test_price_total_only_on_the_manager_s_rows`.
- `test_contract_card_api.py`: `test_a_contract_at_a_site_the_reader_holds_no_role_at` (flips:
  shown).
- `test_contract_calls_api.py`: `ANSWER_KEYS` (`site_code` → `warning_sites`),
  `test_a_contract_of_another_site_is_404` (flips: 200), `test_warnings` (needs a covered machine for
  `no_assignable`), `test_rows_follow_ticket_access` (unchanged meaning, re-run).
- `test_contract_renewal_api.py`: `test_engineer_renews_a_contract` (no `site_id` in the row),
  `test_renewal_skips_scrapped_and_moved_machines` (the moved machine is copied),
  `test_an_inactive_site_is_refused` (removed), `test_the_body_is_checked` (another site's `site_id`
  ignored), `test_renew_needs_edit_at_the_site` (an engineer of B renews: 201; an operator: 403
  `FORBIDDEN_TEXT`), `test_detail_offers_the_renewal`, `test_no_renewal_offered_when_inactive` (no
  inactive-site case).
- `test_contract_alerts.py`: `TestNotInTheApi::test_the_markers_are_not_sent` (`?site_id=` filter),
  `TestHandler::test_push_to_engineers_and_managers_of_the_site`,
  `test_a_manager_with_no_units_gets_both` (the contract needs a line at the site),
  `TestThroughTheWorker::test_scan_alert_and_sends_all_done`.
- `test_alerts_core.py`: `test_message_tag_and_quiet`, `test_ends_today` (the title), `you_get`'s
  `test_engineer_all_units`, `test_manager_at_two_sites`, `test_manager_at_one_unit`,
  `test_a_manager_without_units_gets_the_contract_lines` (the new line text); the helper `_contract`
  (`test_alerts_core.py:548`) with `site_codes`.
- `test_email_core.py`: `test_subject_and_body`; the helper `_contract_facts`
  (`test_email_core.py:142-146`).
- `test_push_api.py`: `TestConfig::test_push_on_with_the_public_key_and_what_you_get` (`:59`):
  "Contracts ending at {site}" → "Contracts ending for machines at {site}".
- `test_rbac.py`: `test_contract_keys` (line 134). `test_role_matrix`: unchanged.
- `test_documents_api.py`: the `db_rows` insert with `site_id` (`test_documents_api.py:557`) fails on
  the dropped column; `TestContractDocuments::test_a_manager_of_another_site_gets_404` (flips),
  `test_an_engineer_here_who_is_manager_elsewhere_is_refused_here` (flips: allowed).
- `test_removed_documents_api.py`: `TestContractRows::test_listed_with_the_title_number_and_site`
  (no site), `test_only_the_sites_manager_sees_them` (any manager),
  `test_it_admin_may_not_restore_or_purge` (`:534`; the line at `:539`): IT admin still refused, but its last line's
  `case.elsewhere` (a manager of another site) now gets 200 on restore, not 404.
- `test_equipment_api.py`: `TestContractFilter::test_no_read_basic_at_the_contract_s_site` (flips).
- `test_migration_squash_v41.py` (S088): `test_production_s_v41_gets_v42_to_v47` breaks (it asserts
  `_versions() == [*range(20, 48)]`). **Kept, redirected:** renamed `test_production_s_v41_gets_v50`;
  asserts `_versions() == [*range(20, 42), 50]`, the v41 description kept, every row kept, the schema
  equal to a fresh `[v41, v50]` build; its docstring follows. It is the strongest production test: a
  database built from the released v20–v41 texts with a ticket, an improvement and a lesson. § 8.1's
  `test_production_at_v41_gets_the_fresh_schema` stays as the targeted check of what v50 adds. The
  file's other five tests pass unchanged.
- `test_modules.py` (`LATEST_VERSION` 50), `test_schema_docs_shell.py`: green once `tooling\schema-docs.bat
  write` has run. `conftest.py` `_TABLES`: no new table.
- `frontend/tests/contractLabels.test.js`: `contractBody` tests (no `site_id`), "contractForm fills
  every field of the empty form" (no `site_id`), "renewalForm …" (`form.site_id`), "renewalNotice
  names the machines copied and skipped" (no "managers of SMTW"), "vendorWarningText names the
  vendor, the site and what to do" (the sites); new: `siteCodesText`.

### 8.4 Browser (e2e)

Changed in `frontend/e2e/contracts.spec.js` (`contractByApi` stops sending `site_id`):
- `S080: the engineer sees the call-out number field and no cost note; the manager sees both` and
  `S080: IT admin adds a contract without the call-out number or the cost note`: no
  `getByLabel("Site")` (`contracts.spec.js:137`, `:151`); assert the dialog has no *Site* field.
- `S080: the engineer does not see another site's contract; the manager sees Edit on both`
  → **important** `S087: the engineer of SMTW sees and edits a contract whose machine is at BRICKS`.
- `S080: the Contracts list fits a phone with no sideways scroll` (`@device`): the *Sites* column and
  the phone line with the machine's site.
- `S081: a machine of another site is not offered in Add machine` → `S087: the engineer's Add machine
  does not offer a machine outside their units` ("No equipment found at your units.").
- `S083: a manager removes a contract document and restores it from Settings`: the row without
  "SMTW"; `SIGNED_LINE` (`:571`) → "Only the managers see these documents and photos.".
- `S085: the engineer renews a contract …` (`:701`): "Prices start empty: the managers enter them on
  the new contract.".
- `S085: an inactive vendor is refused on renewal beside the Vendor field` (`:756`): its header
  assertion `${other.name} · SMTW` becomes the vendor name alone (`contractToRenew` with
  `machines = 0`, `:660`, has no line, so no site, § 5.10).
- `S086: the contract page warns when no Team record is linked to the vendor` (`:937-949`): the test
  shows `no_assignable` (`:947-949`) on a contract with no machine (`:940`). Under § 5.7 a contract
  with no line shows only `no_linked`, so the test puts an SMTW machine on the contract
  (`lineByApi`) before the `no_assignable` step; the text then reads "… can be assigned at SMTW. …"
  (`warning_sites` `["SMTW"]`).
- `frontend/e2e/notifications.spec.js:204`, `:265`: "Contracts ending for machines at SMTW" and
  ", by email".

New, untagged; each flow test calls `expectDialogFits` on the dialog it opens:
- **important** `S087: the manager adds machines of SMTW and BRICKS to one contract; the page and the list show BRICKS, SMTW`
  — Add machine twice; both lines with their paths; the header "· BRICKS, SMTW"; Masters ›
  Contracts' *Sites* "BRICKS, SMTW".
- `S087: the Site filter lists the contracts with a machine at that site`.
- `S087: the Add contract dialog has no Site field and saves` (may fold into S080's add test).

**Runs** (settings: *Browser tests*): targeted `tooling/run-e2e-tests.bat e2e/contracts.spec.js
e2e/notifications.spec.js e2e/screens.spec.js` (the ticket contract line, the card and the removed
row are tested in `contracts.spec.js`; `settings.spec.js`'s one contract line is the task name,
unchanged); the whole suite at Normal once at the end. No shared file changes (`FormModal.vue`, `useFormModal.js`, `api.js`, the router,
the auth store, `e2e/support/`), so no extra WebKit run.

### 8.5 On a real device

None: a field gone, a column and texts, which a browser engine judges.

### 8.6 Acceptance and the SMTW-Review point

- All unit suites green; `tooling\schema-docs.bat check` exits 0; the targeted and Normal runs green.
- By screen: "VP Power UPS AMC 2026–27" with UPS01 (SMTW.MCC2), UPS02 (BRICKS.FILTER): the page
  header "VP Power · BRICKS, SMTW"; the SMTW engineer and the BRICKS engineer both open it and see
  the call-out number; each UPS page shows the card; the SMTW engineer's Add machine finds no BRICKS
  machine; the 60-day reminder reaches the engineers and managers of SMTW and BRICKS.
- **§ SMTW-Review point** (for `.claude/CLAUDE.md`): "**Contracts across sites (S087):** a contract
  has no site (v50); the four contract keys are global (not in `SITE_SCOPED`) and checked with
  `has_perm` / `check_perm`. Its sites are its machines' current sites, through
  `contracts_core.LINE_SITE_JOINS` only: the page's `site_codes`, the list's Site filter, the
  reminders' recipients and the calls' `complete`. Add machine still keeps to the adder's units
  (`_check_node`). A new contract route that checks a key at a site, or stores a site on a contract,
  breaks S087."

## 9. Open questions and assumptions

- **Q1. Reminders: the machines' sites, or every holder company-wide? (KLA to decide.)**
  - **(a) The holders at the sites of the contract's machines — recommended** (§ 5.6). The people of
    the plants the machines stand in. A contract that adds a site's machine reaches that site from
    then on.
  - (b) Every holder of the key, company-wide: the same as who may read it (decision 1); simpler (no
    line query), but an SSVT engineer gets the SMTW compressor AMC's reminders.
- **Q2. A contract with no line: every holder, or nobody?** Only under Q1 (a).
  - **(a) Every holder company-wide — recommended:** a reminder is never lost; such a contract is
    rare (entered, never filled).
  - (b) Nobody: no machine, no site to remind; the contract may end unnoticed.
- **Q3. Restore and purge of a contract document: `equipment:purge_documents` held at any site —
  recommended (§ 5.9)** — or held at a site of the contract's machines? (a) Any site: one rule with
  the reads; a site-less record, as a model's documents. (b) At a machine site: a site-scoped purge
  over a company-wide record, and a contract with no line could never be purged.
- **Q4. Remove a machine: any editor (recommended, unchanged S081)** — or only one inside the
  remover's units? (a) Unchanged: the history line records who removed it. (b) The SMTW engineer
  could no longer take a moved-away machine off; a unit check on a write S081 kept simple.
- **Q5. One step or two?** 41 code and test files, 6 removed (§ 3). **Recommended: one step.** The API's shape
  (the list's flags, `site_codes`, no `site_id`) and the screens change together; a split needs a
  temporary shape. **The split line, if the orchestrator prefers it:** S087 = migration, keys,
  backend routes, alerts, documents and all backend tests, with the list still sending per-site flags
  (each the global value) so the old panel works; S088 = the screens, `contractLabels.js`, the frontend
  unit test and the e2e tests. **Decided by KLA, 31-10-2026: one step.**
- **Q6. Masters › Contracts opens on *All sites* (recommended) or on the user's one site?** (KLA, gate
  A; § 5.10.) (a) *All sites* for everyone: one rule, no per-user state, nothing hidden by default.
  (b) Preselect the user's site when they hold a membership at exactly one site: a shorter list for a
  site's engineer, but a contract with no machine, or with machines elsewhere, is hidden until the
  filter is cleared.
- **A1. Production is at v41** (last release v0.1.14, `e77d635`) and holds none of v50's tables or
  columns (§ 4.2 (b)). Not load-bearing: had a release gone out with v42–v47, v50 would converge it
  as it converges a dev database, which is the decision; no precondition either way.
- **A2. The holders do not change**, only where the keys are checked (`config_rbac.py:163-166`).
- **A3. `EquipmentPicker`'s `siteId` and `emptyText` props are removed** (F10): no caller after S087.
  (An improvement's ticket dialog filters by site through the equipment list itself,
  `AddTicketDialog.vue:43`, not through the picker.)
- **A4. MariaDB's `DROP FOREIGN KEY IF EXISTS`, `DROP INDEX IF EXISTS` and `DROP COLUMN IF EXISTS`**
  give a Note, no error, on a table without them: checked on MariaDB 11.4 in brief review round 3
  (§ 4.1); § 8.1's tests keep the record.
- **A5. S087 is coded on the working tree with S088 in it** (S088 coded, at gate B, snapshot
  `refs/steps/S088`, f5bbb38, uncommitted; Baseline above). S088 is committed before S087's gate B
  snapshot, so S088's commit lands first and S087's diff is its own. `_MIGRATIONS` holds v41
  (squashed) and v50; the helpers are in `tests/migration_helpers.py`; S088's fixture
  `migrations_v41.py` (v20–v41) holds the released texts.
- **Plan and roadmap departure** (recorded): Plan.MD § 2 item 9's "one site per contract" and R02
  Q1.5 (a) are reversed; D5 and D10's "of the contract's site" no longer hold; the orchestrator
  records them in R02's log at gate A.
- **Standards *to verify*:** ISO 55001:2024's clause number for outsourcing (as S080–S086).

- **Answered at gate A by KLA, 31-10-2026 ("Approved"):** the recommended answers: Q1 (a) the holders at the machines' sites; Q2 (a) every holder company-wide for a contract with no line; Q3 (a) `equipment:purge_documents` at any site; Q4 (a) any editor; Q6 (a) *All sites*. Q5 was decided earlier (one step).

## 10. Amendments

### A1 — Add machine asks for the site first (KLA, 31-10-2026; approved by the request)

KLA: "In Add machine, before Equipment code is input, ask the user to select the site. It will help
narrow down the list for the equipment box."

- **What:** the *Add machine* dialog (`ContractMachineDialog.vue`) shows a **Site** select above the
  equipment search. Its options are the active sites where the adder has a unit (the adder's units,
  as `accessible_unit_ids` gives them; all active sites for a user with every unit). With one site,
  it is chosen already. The search (`EquipmentPicker`) stays disabled with the hint "Choose a site
  first." until a site is chosen, and then searches only that site (`site_id` on
  `GET /api/equipment`, the filter that exists). Changing the site clears the search and any machine
  picked.
- **Departure from F10:** `EquipmentPicker`'s `siteId` prop comes back (S087 removed it as unused);
  `emptyText` stays removed unless the coder needs it for "No machine of SMTW matches.".
- **No API change:** the route's rules are unchanged (any site, inside the adder's units). The site is
  a filter of the screen only and is not sent with the line.
- **Tests:** an e2e test (contracts spec): open *Add machine*, the search is disabled, choose a site,
  search, only that site's machines are listed; the existing Add machine tests choose the site first.

## Review log

### Round 1 — 2-brief-review-r1.md (Fable), answered 31-10-2026

Sections changed: header (Baseline), § 3 (intro, Backend, Frontend, Tests, Docs, file count),
§ 4.2, § 5.1, § 5.4, § 5.6, § 5.10, § 7 F2 and F10, § 8.2, § 8.3, § 8.4, § 9 Q5, Q6 (new), A1, A3.

| Finding | Answer |
|---|---|
| BR1-01 minor | Accepted: `test_push_api.py::TestConfig::test_push_on_with_the_public_key_and_what_you_get` and `test_removed_documents_api.py::TestContractRows::test_it_admin_may_not_restore_or_purge` added to § 8.3; e2e `S085: an inactive vendor is refused on renewal beside the Vendor field` added to § 8.4; `test_push_api.py` in § 3 Tests (18 files; 39 code and test files). |
| BR1-02 minor | Accepted (a): `ContractFields.vue:172` → "Only the managers see this note." in § 3 Frontend and § 5.10. |
| BR1-03 minor | Accepted: § 5.10 states the opening value *All sites* (recommended) and the alternative; § 9 Q6 asks KLA at gate A. |
| BR1-04 minor | Accepted (a): § 8.3 gives `test_an_engineer_of_another_site`'s new outcomes (stranger 400 `CHOOSE_MACHINE`, `operator_here` 201); § 8.4 has the S086 warning test put a machine on the contract before the `no_assignable` step. |
| BR1-05…BR1-13 nits | All accepted: Baseline 26810aa and § 3's intro (BR1-05); `covered_sql(coverage, today)`, no `can_read` (BR1-06, § 3, § 5.1, § 5.4, § 8.2); the picker's `siteId` and `emptyText` removed under F10's one rule (BR1-07, § 3, § 7 F10, § 9 A3); the docstrings and `_LINE_SELECT` named (BR1-08, § 3); the `equipment_documents` line of `notes.json` (BR1-09, § 3 Docs); recipients in one query, `people_with_role_at_sites` over a `site_ids` list, inactive sites included (BR1-10, § 3, § 5.6, CLAUDE.md line); targeted e2e run `contracts`, `notifications`, `screens` (BR1-11, § 8.4); A1 not load-bearing (BR1-12, § 4.2, § 9 A1); the unreachable `read_basic` 404 kept as the fail-closed habit, with the reason (BR1-13, § 5.1). None rejected. |

### Round 2 — 2-brief-review-r2.md (Fable), answered 31-10-2026

| Finding | Answer |
|---|---|
| BR2-01…BR2-02 nits | Accepted: `TestCoveredSql::test_no_site` named as removed in § 8.3 (BR2-01); the `case.elsewhere` line is `:539` in a test starting at `:534` (BR2-02, § 8.3). |

**KLA's design change, 31-10-2026 (after round 2):** v42–v47 and S087's change are squashed into one
migration v50, after S088's squash of v20–v41 (F12). Sections changed: header (Baseline, the S088
dependency), § 1 item 1, § 2 (ISO 9001 line), § 3 (Backend `local_db.py`, Tests, Docs, file count),
§ 4.1, § 4.2, § 7 F2 and F12 (new), § 8.1, § 8.3 (`test_modules.py`), § 8.6 (SMTW-Review point),
§ 9 Q5, A1, A5 (new).

### Round 3 — 2-brief-review-r3.md (Fable), answered 31-10-2026

| Finding | Answer |
|---|---|
| BR3-01 minor | Accepted (a): § 8.1 lists the constraint and data tests moved from `test_migration_v42.py`, `_v43.py`, `_v44.py`, `_v45.py`, `_v47.py` to `test_migration_v50.py` on the fresh build, with an `_add_contract` without `site_id`, and adds `test_a_half_applied_v50_converges` on the `test_migration_v45.py:99-109` pattern. |
| BR3-02…BR3-07 nits | Accepted: step 5 is seven statements (BR3-02, § 4.1); the `IF EXISTS` forms stated exactly, checked in round 3 (BR3-03, § 4.1, § 9 A4); the `"migration"` line in the schema diff (BR3-04, § 8.1); S088's helper module named (BR3-05, § 8.1); row (c)'s version ranges (BR3-06, § 4.2); BR3-07 (`INDEX.md`) is the orchestrator's, no brief change. |

### Staleness s1 — 2-brief-review-s1.md (Fable), answered 31-10-2026

| Finding | Answer |
|---|---|
| BS1-01 minor | Accepted (a): `test_migration_squash_v41.py::test_production_s_v41_gets_v42_to_v47` kept, renamed `test_production_s_v41_gets_v50` and redirected (§ 8.3); § 3's count is 20 test files written, 41 code and test files (§ 3, § 9 Q5). |
| BS1-02 minor | Accepted (b): Baseline `26810aa + uncommitted S088 (refs/steps/S088, f5bbb38)`; A5 reworded: S087 is coded on the working tree with S088 in it, and S088 is committed before S087's gate B snapshot (header, § 9 A5). |
| BS1-03…BS1-08 nits | Accepted: `local_db.py` anchors and S088's header comment (BS1-03, § 3, § 4.1); the v13 fixture sentences (BS1-04, § 4.1); `SQUASHED` and the build order of the v47 shape (BS1-05, § 8.1); the half-applied test's pattern anchored to `test_a_half_applied_v41_re_runs` (BS1-06, § 8.1); the *Migrations (S025, S088)* bullet and § SMTW-Review *Migrations* lines (BS1-07, § 3 Docs); `LATEST_VERSION` follows the last entry (BS1-08, § 3). |
