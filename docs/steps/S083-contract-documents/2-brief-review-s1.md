```
Step: S083 — Contract documents
Doc: brief-review s1
Author: Brief reviewer (Fable)
Date: 31-10-2026
```

Reviewed against: d216f48 + uncommitted S079, S080, S081, S082 (and the R02 docs)

# S083 — Staleness review s1

**Verdict: no blocker or major finding. Three minor findings (names and one lock-note sentence in
`contracts.py`, and a helper S081 added that the brief's plan duplicates) and six nits. The design
and the decisions KLA approved (E1, E2, Q1 a) stand; the coder can start once the brief's text is
fixed.**

Mode: staleness (README § Stale brief check). I read the approved brief, the facts file
`scratch/brief-facts-S083.md` (re-run today), and the working tree's `backend/contracts.py`,
`backend/auth_utils.py`, `backend/config_rbac.py`, `backend/local_db.py` (v42–v44), `backend/equipment.py`
(LOCK ORDER), `backend/documents.py`, `backend/documents_core.py`, `backend/file_store.py`,
`frontend/src/views/ContractView.vue`, `frontend/e2e/contracts.spec.js`, the contract tests, the S080–S082
impl reports and the S084 brief's lock note. One question only: does each statement of the brief about
that code still hold? I did not re-review the rest of the brief.

## Findings

### BS1-01 — minor — § 3 and § 6.1 name S080's code as its brief planned it, not as it was coded

**What changed.** S080–S082 coded `contracts.py` with different names from the ones the brief carries
"(from S080)":

- `_fetch_contract` does not exist. The plain read is `_contract_row(cur, contract_id)` (the full
  `_CONTRACT_SELECT` row); the write lock is S081's `_lock_contract(cur, contract_id)` (see BS1-03).
- `_contract_out` takes three arguments, `_contract_out(row, flags, today)`, not `(row, flags)`.
- The flags are not built in `_contract_out`. `_SiteFlags.at(site_id)` builds the dict
  `{can_edit, can_read_callout, can_read_cost}` once per site in the request, and `_contract_out` does
  `item.update(flags)`. There are three flags today, not the two the brief lists.
- `_sites_holding` is gone: `auth_utils.sites_holding(cur, key)` exists as S082 states, returns
  `[{id, code, name, active}, …]` ordered by code, and `contracts.py` and `equipment.py` already import it.

**What in the brief is now wrong.** § 3 "(from S080)": `_contract_out(row, flags)`, `_fetch_contract`,
"the flags `can_edit`, `can_read_cost`". § 3 Backend: "the two flags … in the flags `_contract_out`
writes". § 6.1: "Computed once per site, as S080's flags" is right, but the place is `_SiteFlags.at`.
§ 9: the assumption "if S082 lands without the move, documents.py imports `contracts._sites_holding`" is
settled.

**Why it matters.** A coder who follows § 6.1 literally adds two `has_perm_at` calls inside
`_contract_out`, once per row of the list, beside S080's once-per-site cache. A coder who looks for
`_fetch_contract` finds nothing and has to guess which of two functions the brief meant.

**Fix (recommended).** In § 3 replace `_fetch_contract` with `_contract_row` (the read) and `_lock_contract`
(the write lock), and write `_contract_out(row, flags, today)` and "the flags `_SiteFlags.at` builds
(`can_edit`, `can_read_callout`, `can_read_cost`)". In § 3 Backend and § 6.1 say the two new flags are
added to the dict `_SiteFlags.at` returns, so every `_contract_out` answer carries them. Drop the
`_sites_holding` fallback from § 9 and say `sites_holding` is checked.

### BS1-02 — minor — one sentence of S081's lock note becomes false and is not on the brief's edit list

**What changed.** S081 wrote `contracts.py`'s LOCK ORDER note after the brief's baseline. Its "No
deadlock cycle" bullet on the node (1) says: "equipment.py's writes (move, scrap, edit), meters.py,
item_properties.py, **documents.py** and tickets.py's raise hold (1) exclusive and never wait on a contract
or a line row". Its first bullet says "The contract row: only this module locks it, always first in its
transaction (the PUT and the three line writes)".

**What in the brief is now wrong.** § 5.4 tells the coder to write three note changes (contracts.py's
LOCK ORDER, equipment.py's two bullets) and the documents.py docstring. It does not name the node (1)
sentence above. After S083, documents.py's contract path does wait on a contract row; it holds no (1)
at that moment, so the reasoning stays sound, but the sentence as written becomes false. The first
bullet's "(the PUT and the three line writes)" also needs the documents path added, which the brief's
quoted text ("Only contracts.py's functions lock contracts rows (documents.py calls
`lock_contract_for_change`)") covers only in part.

**Why it matters.** The lock notes are the self-check's item (2) (`.claude/CLAUDE.md` § Step workflow,
*Self-check, repo items*, which since S081 names `contracts.py`); a sentence that says documents.py never
waits on a contract row misleads the next step that reasons from it (S084's scan, S085, S086).

**Fix (recommended).** Add to § 5.4's "The coder writes" list: in contracts.py's node (1) bullet,
"documents.py's node path holds (1) exclusive and waits on no contract row; its contract path (S083)
holds the contract row and no (1)"; and in the first bullet, "(the PUT, the three line writes, and
documents.py's writes through `lock_contract_for_change`)". No design change.

### BS1-03 — minor — `lock_contract_for_change` duplicates S081's `_lock_contract`

**What changed.** S081 added `_lock_contract(cur, contract_id)` to `contracts.py`: `SELECT * FROM contracts
WHERE id = %s FOR UPDATE` → 404 unless `contract:read_basic` is held at `site_id` → `require_perm_at(EDIT,
site_id)` 403 → the locked row. That is the brief's § 5.1 `lock_contract_for_change(cur, contract_id,
key)` with `key = contract:edit`, minus the `contract:read_senior` check.

**What in the brief is now wrong.** § 5.1 plans a second function with the same lock and the same 404,
and a private `_contract_access` beside the checks `_lock_contract` already makes. A planned duplicate
of an existing helper (CLAUDE-COMMON *DRY*).

**Options.**
- (a) **Recommended.** Give `_lock_contract` a `key` parameter (`_lock_contract(cur, contract_id,
  key=EDIT)`) and let `lock_contract_for_change(cur, contract_id, key)` be `locked = _lock_contract(cur,
  contract_id, key)` then `require_perm_at(READ_COST, locked["site_id"])`. `_contract_access` then holds
  only the plain-read case (`read_contract`, `read_contract_for_change`), or disappears if those two
  make the same three checks inline. The order of the two 403s (`read_senior` before `key`) is then
  reversed for the lock path; both answer 403 with the same message, so no screen or test can tell.
- (b) Keep the brief's three functions and `_contract_access` as planned, and say in § 5.1 that
  `_lock_contract` stays for the line writes. Two functions lock the same row with the same 404 rule.

### Nits

- **BS1-04** (nit) § 4.1: `backend/local_db.py:1511` for `_PRECONDITIONS` is now `:1589` (anchor
  refresh). `config_rbac.py:99`, `documents_core.py:57` and `documents.py:306` still hold.
- **BS1-05** (nit) § 6.1 and § 8.3: `_contract_out` has a fifth caller since S082, the card route
  `contracts_for_equipment`, which cuts the answer to `_CARD_KEYS`; the two new flags never reach the
  card, and `test_contract_card_api.py:100` (an exact-item assert) stays green only for that reason.
  Say so, and that the list's `sites` array (`can_add`, `can_read_callout`, `can_read_cost` per site)
  does not gain them.
- **BS1-06** (nit) § 8.3 first bullet, "*To check when coding*: S080 is not coded yet": now checked.
  `test_contracts_api.py` asserts the flags as tuples of named keys (lines 84, 98, 105), never a whole
  key set, so nothing breaks; replace the bullet with that.
- **BS1-07** (nit) § 3 Backend, `contracts.py`: the module docstring's ACCESS paragraph (S080–S082) names
  the four keys and what each reads; add "and the documents rule (S083)" to the edit, beside the LOCK
  ORDER note.
- **BS1-08** (nit) § 3 Docs, `.claude/CLAUDE.md` § SMTW-Review: S081 already ended the *Contract fields
  by key* point with "R02.3's documents join this rule."; the coder replaces that sentence rather than
  appending "and its documents (S083)".
- **BS1-09** (nit) § 3 "(from S080)": the 403 text in § 5.1, "You can't do this at SMTW", holds
  (`auth_utils.require_perm_at`), and `make_vendor` (`conftest.py:451`) posts as `admin`, not IT admin as
  its docstring says; no effect on `contract_case`.

## Checked and found consistent

- **Migration number:** `_MIGRATIONS` ends at v44 (S081), `LATEST_VERSION` 44; S083's **v45** is next.
  S084's brief takes **v46** (its § 4.1 names S083's v45). `test_modules.py` reads `LATEST_VERSION`.
- **v45's SQL:** `contracts` (v43) exists with `id`, `site_id`, `title`, `contract_number`, `active`;
  `equipment_documents.procedure_id` is the last owner column (v41), so `AFTER procedure_id` holds; the
  v41 entry's last three statements are the pattern the brief cites; `_PRECONDITIONS` holds 20, 25, 34.
- **Owner table:** `file_store._OWNER_FOLDERS` has the five owners; `documents.OWNERS` has the five
  `Owner(column, path, log_name, read, read_for_change, lock_for_change, lock_for_purge, read_key,
  write_key, purge_key)` entries, so the brief's § 5.1 entry fits the dataclass; the five `_*_DOCS` /
  `_FOR_*` pairs and the eight routes exist as named. `documents.py`, `documents_core.py` and
  `file_store.py` are unchanged since d216f48.
- **Blueprints and URLs:** `documents_bp` at `/api`, `contracts_bp` at `/api/contracts` with the routes
  `/`, `/<int:contract_id>`, `/<int:contract_id>/equipment[/<int:equipment_id>]` and
  `/for-equipment/<int:node_id>`; none ends in `/documents`.
- **Imports:** `contracts.py` imports `equipment`, `masters`, `contracts_core`; `masters.py` and
  `equipment.py` import nothing from `documents.py`; so `documents.py` → `contracts.py` adds no cycle,
  and `contracts.py` never imports `documents.py`.
- **Keys:** `contract:read_basic` `('*',)`, `contract:read` engineer, `contract:read_senior` manager,
  `contract:edit` engineer and IT admin, all in `SITE_SCOPED`; `equipment:purge_documents` manager and IT
  admin, site-scoped; `ROLE_INCLUDES` gives the manager the engineer's keys; `test_role_matrix` asserts
  these. `has_perm_at`, `require_perm_at`, `sites_holding` as the brief uses them.
- **The site never changes:** `change_contract` refuses a different `site_id` (`SITE_KEPT`).
- **§ 5.4 against S084:** S084's brief (§ 5.4) says its scan locks several contract rows `FOR UPDATE` in
  id order and is the only path to hold more than one; the documents path holds one and waits on no
  other after it. No cycle.
- **`equipment.py`'s contracts.py bullet** (from S081) reads "Only contracts.py locks contracts and
  contract_equipment rows"; the brief's replacement text fits.
- **`ContractView.vue`:** the *Machines covered* card (`data-testid="contract-machines"`) is the last
  card; after it only `ContractMachineDialog`; no documents placeholder (S081 B8 holds); the page reads
  `can_edit`, `can_read_cost`, `can_read_callout` from the detail.
- **`contracts.spec.js`:** in-spec helpers `callAs`, `vendorByApi`, `contractByApi(vendor, title,
  fields, key = "manager")`, `siteId`; the seed's `manager` is `maint_manager` at SMTW and BRICKS, the
  `engineer` `maint_engineer` at SMTW. `settings.spec.js` and `equipment.spec.js` exist;
  `"Add document"` is used in `equipment.spec.js:96` and `journeys.spec.js:80`.
- **Existing tests:** `test_removed_documents_api.py:151` (`item["owner"] in ("model", "procedure")`)
  and `test_who_may_list` as § 8.3 states; `_scoped_branch(branch_sql, search_column, unit_column, …)`
  takes a site-id list as its `unit_ids` without change; `_removed_item`'s `else` branch is the node's,
  so the contract needs its own case as § 5.5 says.
- **Docs:** `docs/schema/notes.json`'s `equipment_documents` line names five owners and "the five
  columns"; Plan.MD § 2 item 9 and the § 3 contract keys paragraph (lines 233–240) exist for the edits
  in § 3 Docs; `RemovedDocuments.vue` has the `v-else-if` chain and the placeholder the brief extends.
- **Facts file:** the one-time scratch PDFs exist (`scratch/AMC14082369550_12606 (1).pdf` and four
  more). Every "not found" name in the facts file is one S083 adds, except the three in BS1-01.

## Feedback

- waste: the facts file's "not found" list tags a name with "planned in S080, S084, S082" when a brief only
  mentions it, so `read_contract` and `lock_contract_for_change` looked like S080's code and I had to
  grep `contracts.py` to learn they are S083's (`scratch/brief-facts-S083.md` line 339, 1 call).
- idea: in a staleness run, `brief_facts.py` could mark a "not found" name whose "planned in" step now
  has a `3-impl-report.md` (here `_fetch_contract`, `_sites_holding`): that is exactly the stale name,
  and the tool already knows both facts.
- hindrance: `cat` of the 40 KB brief went over the Bash output limit and was spooled to a file, so I read
  it again with Read (1 call lost); the spawn prompt could say briefs are read with Read, not `cat`.
