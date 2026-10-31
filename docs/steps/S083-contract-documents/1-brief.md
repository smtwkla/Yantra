```
Step: S083 — Contract documents
Doc: brief
Author: Orchestrator's drafter (Opus)
Date: 30-10-2026
Track: full
Baseline: refs/steps/S082 (185d524; d216f48 + S079, S080, S081, S082), checked by staleness review s1
Status: Committed 6a32fee (adopted 31-10-2026); important checks pending: row 60 of device-checks.md (IT Admin); was: Gate B 31-10-2026 (code review r1: 1 minor, 1 nit, fixed in fix round 1; verify review r2: no finding); implementing 31-10-2026 (staleness s1: 0 blocker, 0 major, 3 minor accepted); approved 30-10-2026 (gate A delegated by KLA for tonight's R02 steps; review r1: 0 blocker, 0 major, 3 minor accepted)
From: R02.3
```

# S083 — Contract documents

## 1. What will be built

S080 gives Yantra the contract record and S081 its page (`/contracts/:id`). **S083 puts the paper on
the contract**: the signed contract, its scope annexure and the vendor's quote, as PDFs or phone
photos, on the contract page. The contract becomes the **sixth owner** of the documents store
(S006), beside the node, the model, the ticket, the countermeasure (S070) and the one-point lesson
(S075). Every document sits behind `contract:read_senior` (D5): a quote or a signed contract shows the
price.

1. **Upload, list, open, download, retitle, remove** a contract's documents and photos, through the
   documents routes of `backend/documents.py`, at `/api/contracts/<id>/documents` (§ 6). Files live in
   `DATA_DIR/contracts/<id>/` (`file_store._OWNER_FOLDERS`).
2. **Who** (§ 5.2): read with `contract:read_senior` at the contract's site (managers; admin by the
   bypass). Write (upload, retitle, remove) with `contract:edit` **and** `contract:read_senior` there.
   Restore and erase (Settings › Removed documents) with `equipment:purge_documents` **and**
   `contract:read_senior` there. So IT admin, who holds `contract:edit` and
   `equipment:purge_documents` but not `contract:read_senior`, sees no contract document anywhere.
3. **The cards on the contract page** (§ 5.7): S081's `ContractView.vue` shows the existing
   `DocumentsCards.vue` (*Documents* and *Photos*) after *Machines covered*, for `can_read_documents`
   holders; others see nothing of them (as for the price).
4. **Settings › Removed documents** lists a removed contract document as "Contract <title>" with its
   site, for the users who may restore or erase it (§ 5.5).
5. **A PDF with blank lines before its header is accepted** (§ 5.6, Q1): the Fuji quote
   `AMC14082369550_12606 (1).pdf` starts with six line feeds, and today's type check refuses it
   (fact, checked below). The check accepts only spaces, tabs and line breaks (`\r`, `\n`) before `%PDF-`, within
   the first 1024 bytes; the stored file keeps its bytes. This applies to every owner.

**Migration v45** (§ 4.1): the column `equipment_documents.contract_id` and the owner CHECK widened to
six. S084 (reminders, drafted in parallel) takes v46 if it needs one.

**After S083:** the manager opens the signed contract from a phone when the vendor disputes what is
covered. The engineer reads the terms (S080's *Covered* / *Not covered*), not the paper (D5; a
correction of the roadmap's "After it", § 9).

### Out of scope

- Documents on the *Under contract* card (S082) or on a ticket's contract line (R02.6): the floor
  holds `contract:read_basic` only (D5).
- A document shared by two contracts (D7's mixed quote): the manager uploads it to each; each owner
  keeps its own copy (§ 7 E6).
- A count bound per contract, document categories (signed contract / annexure / quote), versions of a
  document. The store has none for any owner.
- Anything that touches the D10 call-out number or the price: none.
- Renewal copying documents to the new contract (R02.4's decision).

## 2. Standards and practice

- **ISO/IEC 27001:2022 A.5.15, access control**, and **A.8.3, information access restriction**. In plain words: each person reaches only the information the work needs, and the
  system, not the screen, enforces it. The files are served only by the documents routes, after the
  read check at the contract's site; the list, the file, the thumbnail and the removed list all
  follow `contract:read_senior` (§ 5.2). An editor who may not read documents may not write them.
- **ISO/IEC 27001:2022 A.8.10, information deletion**. In plain words: delete
  information when it is no longer needed, in a controlled way, and keep a record. Erasing stays
  S008's two steps (remove, then erase from Settings), logged with who uploaded, who removed and
  who erased.
- **ISO 9001:2015 § 7.5.3, control of documented information.** In plain words: keep the documents
  that show what was agreed available where they are needed, and protect them from loss, wrong use
  and unwanted change. The signed contract is stored on the contract, never edited (only its title),
  removed only by hiding (the file stays until a manager erases it), with who and when on each row.
- **ISO 55001 § 8.3, outsourcing** (cited in Plan.MD § 2; the number in the 2024 edition *to
  verify*). In plain words: work given to an outside firm stays the plant's responsibility; the
  plant controls it and keeps the evidence. The vendor's signed scope is the evidence of what the
  plant bought.

## 3. Where

S079–S082 are coded before S083. In the files they change this brief anchors by name, not by line
(README § Anchors by name). Names marked **(from S080)**, **(from S081)** or **(from S082)** do not
exist at the baseline; they are as those briefs state them:
- (from S080): the table `contracts` (`site_id`, `title`, `contract_number`, `active`);
  `backend/contracts.py` with `contracts_bp`, `_contract_out(row, flags, today)`, the plain read
  `_contract_row(cur, contract_id)`, S081's write lock `_lock_contract(cur, contract_id)`, its LOCK
  ORDER note and its ACCESS docstring paragraph; the keys `contract:read_basic`,
  `contract:read_senior`, `contract:edit` in `SITE_SCOPED`; the flags dict `_SiteFlags.at(site_id)`
  builds once per site (`can_edit`, `can_read_callout`, `can_read_cost`); `backend/tests/test_contracts_api.py`;
  `frontend/e2e/contracts.spec.js` with its in-spec set-up helpers; the fixture `make_vendor` (from
  S079, `backend/tests/conftest.py`).
- (from S081): `frontend/src/views/ContractView.vue`, the route `/contracts/:id`, migration v44, the
  rewritten `contracts.py` bullet of `backend/equipment.py`'s LOCK ORDER.
- (from S082): `auth_utils.sites_holding(cur, key)` (S080's `_sites_holding`, moved and unchanged:
  the rows `{id, code, name, active}` of the sites where the user holds the key).

### Backend

- `backend/local_db.py`: migration **v45** at the end of `_MIGRATIONS` (§ 4.1). No `_PRECONDITIONS`
  entry.
- `backend/contracts.py` (from S080; S083 adds): the documents owner's three functions
  `read_contract`, `read_contract_for_change`, `lock_contract_for_change` (§ 5.1; the lock built on
  S081's `_lock_contract`, which gains a `key` parameter), and the two flags `can_read_documents`,
  `can_edit_documents` in the dict `_SiteFlags.at` returns (§ 6.1). The LOCK ORDER note gains the
  documents path (§ 5.4); the ACCESS docstring paragraph gains the documents rule. contracts.py
  never imports documents.py.
- `backend/documents.py`: `OWNERS["contract"]`; a sixth stacked route decorator `_CONTRACT_DOCS` /
  `_FOR_CONTRACT` on the eight documents routes (`list_documents`, `upload_document`,
  `get_document_file`, `get_document_thumb`, `update_document_title`, `remove_document`,
  `restore_document`, `purge_document`); `_REMOVED_CONTRACT_BRANCH` in `_removed_branches`, its case
  in `_removed_item` (§ 5.5); `_read_upload` passes `data[:HEADER_WINDOW]` to `detect_file_type`
  (§ 5.6), and the now unused `SIGNATURE_BYTES` leaves its import list (it stays in documents_core
  for the WebP rule); the module docstring (owners, locks). It imports the three functions from contracts.py and
  `sites_holding` from `backend/auth_utils.py`.
- `backend/documents_core.py`: `HEADER_WINDOW = 1024`, the leading-whitespace rule in
  `detect_file_type` (§ 5.6).
- `backend/file_store.py`: `_OWNER_FOLDERS` gains `"contract": "contracts"`; the docstring's layout
  line.
- `backend/equipment.py`: docstring only. The documents.py bullet of the LOCK ORDER names the
  contract row as a sixth owner lock; the contracts.py bullet (from S081) names the documents path
  (§ 5.4).

### Frontend

- `frontend/src/views/ContractView.vue` (from S081): the cards or the line (§ 5.7).
- `frontend/src/views/settings/RemovedDocuments.vue`: a `v-else-if="item.owner === 'contract'"`
  cell, the docstring, and the search placeholder gains "contract" (§ 5.5).
- `frontend/src/components/documents/DocumentsCards.vue`: no change (its props cover the case:
  `basePath`, `canEdit`).

### Tests

- `backend/tests/test_migration_v45.py` (new), on the pattern of `test_migration_v41.py` (§ 8.1).
- `backend/tests/test_documents_api.py`: a class `TestContractDocuments` with its fixture
  `contract_case`; `TestOwnerCheckConstraint` gains the six-owner case; a PDF with leading blank
  lines in `TestUploadAndServe` (§ 8.2).
- `backend/tests/test_documents_core.py`: `TestDetectFileType` gains the whitespace cases (§ 8.2).
- `backend/tests/test_removed_documents_api.py`: a class `TestContractRows` (§ 8.2).
- `backend/tests/test_contracts_api.py` (from S080): the two flags (§ 8.2, § 8.3).
- `frontend/e2e/contracts.spec.js` (from S080): the S083 tests (§ 8.4).

### Docs (housekeeping, by the coder)

- `docs/schema/notes.json`: the `equipment_documents` line names the sixth owner (`contract_id`,
  S083, v45, its index) and "the six columns"; then `tooling\schema-docs.bat write`, read
  `git diff docs/schema/`, and `check` exits 0. `docs/schema/schema.json` and
  `docs/schema/schema-data.js` are generated.
- `docs/Plan.MD` § 2 item 9: "the signed contract, its annexures and the vendor's quotes are attached
  to the contract (documents and photos, `contract:read_senior` to read; `contract:edit` with
  `read_senior` to add)"; § 3, the contract keys' paragraph (from S080): the documents rule and IT
  admin's exclusion from contract documents (§ 7 E2).
- `.claude/CLAUDE.md`: § Yantra Specifics, *Files (S006)*: six owners, the sixth the contract
  (S083, `contracts/<id>/`; read with `contract:read_senior` at its site, written with
  `contract:edit` and `contract:read_senior` there, restored and erased by
  `equipment:purge_documents` with `contract:read_senior` there); § SMTW-Review, S080's point
  *Contract fields by key*: the sentence "R02.3's documents join this rule." is replaced by the
  documents rule (S083).
- `docs/steps/device-checks.md`: one row (§ 8.5).
- `docs/Keycloak.md`: no change (no role changes).

**File count:** 14 code and test files (6 backend code, 2 frontend code, 5 backend test files and
the spec), 5 docs. One concern.

## 4. Data model

### 4.1 Migration v45

```sql
-- A contract's documents and photos (S083, R02.3): the sixth owner of the documents store.  The
-- owner CHECK is dropped and added again with its name, as v38 and v41 did; every existing row has
-- one of the five owners and contract_id NULL, so it meets the new CHECK.
ALTER TABLE equipment_documents
    ADD COLUMN IF NOT EXISTS contract_id INT NULL AFTER procedure_id,
    ADD KEY IF NOT EXISTS ix_equipment_documents_contract (contract_id, removed_at),
    ADD CONSTRAINT fk_equipment_documents_contract
        FOREIGN KEY IF NOT EXISTS (contract_id) REFERENCES contracts (id);
ALTER TABLE equipment_documents DROP CONSTRAINT IF EXISTS chk_equipment_documents_owner;
ALTER TABLE equipment_documents ADD CONSTRAINT IF NOT EXISTS chk_equipment_documents_owner
    CHECK ((equipment_id IS NOT NULL) + (model_id IS NOT NULL) + (ticket_id IS NOT NULL)
           + (action_id IS NOT NULL) + (procedure_id IS NOT NULL) + (contract_id IS NOT NULL) = 1);
```

- Three statements in the `_MIGRATIONS` entry `(45, "Contract documents (S083)", [...])`, as v41's
  last three (`backend/local_db.py`, the v41 entry).
- **Foreign key:** no `ON DELETE`, so `RESTRICT`, as every foreign key; a contract is never deleted
  (S080: inactive instead).
- **`ix_equipment_documents_contract (contract_id, removed_at)`** serves the list
  (`contract_id = ? AND removed_at IS NULL`), as the action and procedure keys do.
- **No precondition** (`_PRECONDITIONS`, `backend/local_db.py:1589`, holds 20, 25 and 34): a nullable
  column, a key, a foreign key no row uses yet, and a CHECK every existing row meets (fact: v41's
  CHECK holds today, so each row has exactly one of the five owners). Nothing is converted or
  dropped. The foreign-key add and the CHECK scan the documents rows; production holds node, model
  and ticket documents, and § 8.1 runs v45 on a v44 database with rows of all five owners.
- **Re-run safety:** `IF NOT EXISTS` on the column, the key, the foreign key and the CHECK; `DROP
  CONSTRAINT IF EXISTS`. A half-applied v45 (the CHECK dropped, not added) runs again and adds it.
- **Order:** the foreign key needs `contracts` (v43, S080), which runs first in the same upgrade.
- **Rollback:** a release before v45 never reads `contract_id`; its documents queries name their
  columns, and its removed-list branches join their own owner, so a contract's document row is
  invisible to it. Its v41 CHECK is gone, and its uploads still meet v45's CHECK (one owner, the
  sixth column NULL).

### 4.2 What is computed, never stored

- The flags `can_read_documents`, `can_edit_documents` (§ 6.1).
- On a removed-list row: the contract's title, its number and its site code (joins).

## 5. Rules

### 5.1 The owner

```python
"contract": Owner("contract_id", "/api/contracts/{}/documents", "contract",
                  read_contract, read_contract_for_change, lock_contract_for_change,
                  lock_contract_for_change, "contract:read_senior", "contract:edit",
                  "equipment:purge_documents"),
```

- `_CONTRACT_DOCS = "/contracts/<int:owner_id>/documents"`, `_FOR_CONTRACT = {"defaults": {"owner":
  "contract"}}`. They live in `documents_bp` (prefix `/api`). `contracts_bp`'s routes are `/`,
  `/<int:contract_id>`, S081's `/<int:contract_id>/equipment[/<int:equipment_id>]` and S082's
  `/for-equipment/<int:node_id>`; none ends in
  `/documents`, so the two blueprints never claim one URL (as tickets and lessons).
- **The functions** (contracts.py, each with a docstring naming documents.py's slot):
  - `_contract_access(cur, row, key)` (private): plain. `contract:read_basic` not held at
    `row["site_id"]` → 404 "Not found"; `contract:read_senior` not held there →
    `require_perm_at` 403 "You can't do this at SMTW"; `key` not `None` and not held there →
    `require_perm_at(key, site_id)` 403.
  - `read_contract(cur, contract_id, _key=None)`: `SELECT id, site_id FROM contracts WHERE
    id = %s` (plain) → 404 when missing; `_contract_access(cur, row, None)`; returns the row.
  - `read_contract_for_change(cur, contract_id, key)`: the same read; `_contract_access(cur, row,
    key)`. A refused upload reads and writes no file (S006 § 5.6).
  - `lock_contract_for_change(cur, contract_id, key)`: built on S081's `_lock_contract`, which gains
    a `key` parameter (`_lock_contract(cur, contract_id, key=EDIT)`; the line writes keep calling it
    as now). `locked = _lock_contract(cur, contract_id, key)` (`SELECT … FOR UPDATE` → 404 without
    `contract:read_basic` at the site → `require_perm_at(key, site_id)` 403), then
    `require_perm_at("contract:read_senior", locked["site_id"])` 403. The two 403s come in the
    other order than on the plain path; both answer the same message, so no screen or test can
    tell (BS1-03). It serves change and purge: no state rule (§ 5.3), as the model's and the
    lesson's. `_contract_access` serves only the two plain reads.
- `read_senior` is checked in every function, so it holds for **every** route of this owner, also
  restore and purge, whose `key` is `equipment:purge_documents`.
- **The site never changes** (S080 § 5.1), so a plain read of `site_id` and the locked one agree; the
  decisions still come from the locked row in the write transaction.
- **Every kind** (`photo`, `document`), as every owner (S018): a phone photo of a signed page is the
  manager's way to file paper.

### 5.2 Permissions

| Action | Route key (`_owner_key`, held at any site) | Then, at the contract's site |
|---|---|---|
| List, file, thumb | `contract:read_senior` | `read_basic` 404, `read_senior` 403 |
| Upload, retitle, remove | `contract:edit` | `read_basic` 404, `read_senior` 403, `contract:edit` 403 |
| Restore, erase | `equipment:purge_documents` | `read_basic` 404, `read_senior` 403, `purge_documents` 403 |
| Removed list | `equipment:purge_documents` (route decorator) | contract rows only at sites holding both `purge_documents` and `read_senior` (§ 5.5) |

- **Holders today** (S080 § 5.5; `backend/config_rbac.py` `PERMISSIONS`): `contract:read_senior`
  `maint_manager`; `contract:edit` `maint_engineer` (so the manager) and `it_admin`;
  `equipment:purge_documents` `maint_manager` and `it_admin` (`backend/config_rbac.py:99`, in
  `SITE_SCOPED`). So the manager of the site reads,
  writes, restores and erases; the engineer, IT admin and the floor do none of it; admin all (the
  bypass).
- **The write rule** (§ 7 E1): `contract:edit` **and** `contract:read_senior`. D5 puts every document
  behind `read_senior`; an editor without it could upload but never list, open, retitle or remove
  what they uploaded. With today's roles the rule equals "the site's managers"; checking both keys
  keeps it right if `contract:edit` and `read_senior` drift apart (as S081 B3's price route).
- **404 before 403:** a user who cannot see the contract learns nothing of it (S080 § 5.5); a
  `read_basic` holder sees the contract page anyway, so a 403 tells them nothing new.
- **A request with no identity** is refused with 401 by `require_auth` before any route, never admin.
- **Identity:** no field changes who can log in or what they see. The list names no person beyond
  the logins in `created_by` / `updated_by`, as every owner.
- **Buttons:** the cards show only with `can_read_documents`; *Add document*, *Add photo*, *Edit
  title*, *Remove* only with `can_edit_documents` (`DocumentsCards`' `canEdit`). So no button ends in
  a 403 (S070 D10).

### 5.3 States

- **No state rule.** An ended, an upcoming and an inactive contract all take, list and lose
  documents. The signed copy often arrives after the period starts, and an inactive contract (entered
  by mistake) may need its paper removed. Restore is never refused by the contract's state, so the
  removed list sends `state` `null` for a contract row (Restore stays enabled).
- **Already in the target state:** a second remove of one document → 404 (one conditional
  `UPDATE`, as today); a restore of a document not removed → 404; an erase of a document not removed
  → 409 "Remove the document first" (`purge_document`, unchanged).
- **No event or alert.** The contract has no timeline; each document row keeps who and when
  (created, updated, removed); restore and erase write `documents.py`'s log lines, as for every
  owner.

### 5.4 Locks

The database runs REPEATABLE READ. A document write takes **one owner lock**, the contract row, first
in its transaction, then only `equipment_documents` rows, which nothing else locks. The contract row
has no number in `backend/equipment.py`'s order; S080 and S081 describe it as contracts.py's own.

**Upload** (`POST /api/contracts/<id>/documents`):
1. Plain, no transaction lock: `read_contract_for_change` (404, 403, 403); `upload_max_mb`.
2. The checks and the thumbnail (`_read_upload`), no lock.
3. The files written (`_write_files`), no transaction open (S006 § 5.6).
4. `transaction`: (C) `SELECT id, site_id FROM contracts WHERE id = %s FOR UPDATE` → 404; plain:
   `_contract_access` (404, 403); the `equipment_documents` insert (a shared foreign-key lock on the
   contract row, held exclusive); the item read back.
5. On any failure in 4, the files just written are removed (unchanged).

**Retitle, remove** (`PUT`, `DELETE …/documents/<doc_id>`): one `transaction`: (C) → plain checks →
the one `equipment_documents` statement.

**Restore, erase** (`POST …/<doc_id>/restore`, `…/purge`): one `transaction`: (C) with `key` =
`equipment:purge_documents` → plain checks → the `equipment_documents` statement; erase then removes
the files after the commit (unchanged).

**Reads** (list, file, thumb, removed list): plain, no lock.

**No deadlock cycle**, checked against the notes (`backend/equipment.py` LOCK ORDER, the documents.py
docstring, and S080's and S081's `contracts.py` notes):
- *(C) the contract row* is taken exclusive by contracts.py's own writes (S080's `PUT`, S081's line
  writes), always first in their transaction, and now by the documents path, also first. Neither
  holds another lock before it. S084 (drafted in parallel) locks several contract rows `FOR UPDATE`
  in its daily scan, in id order (`alerts.lock_contract_for_scan`, S084 § 5.4); the documents path
  holds one contract row and waits on no other contract row after it, so no cycle forms. The
  staleness check re-reads S084's note.
- *After (C)*, contracts.py's writes take the vendor, the node (1) or a `contract_equipment` row; the
  documents path takes only `equipment_documents` rows. No other path locks a document row, and no
  path that holds a vendor, node or line lock waits on (C). So a document write waiting on (C) waits
  behind a contract write that finishes, and the reverse.
- *Two document writes on one contract* serialise on (C), which also serialises a title edit with a
  remove (S006 § 5.8). The documents path never holds two owners' locks.

The coder writes: in contracts.py's LOCK ORDER note, "documents.py (S083) locks the contract row FOR
UPDATE through `lock_contract_for_change`, first in its transaction, then touches only
`equipment_documents` rows"; in equipment.py's documents.py bullet, "… a lesson's procedures row
(6d), or a contract row (contracts.py, S083); never two owners'"; in S081's contracts.py bullet,
"Only contracts.py's functions lock contracts rows (documents.py calls `lock_contract_for_change`)";
in contracts.py's first bullet, "(the PUT, the three line writes, and documents.py's writes through
`lock_contract_for_change`)"; in contracts.py's node (1) bullet, "documents.py's node path holds (1)
exclusive and waits on no contract row; its contract path (S083) holds the contract row and no (1)"
(BS1-02); and the documents.py docstring's *Locks* paragraph.

### 5.5 The removed list

`_REMOVED_CONTRACT_BRANCH` (the columns of every branch, in their order):

```python
_REMOVED_CONTRACT_BRANCH = (
    f"SELECT {_REMOVED_DOC_COLUMNS}, 'contract' AS owner, c.id AS owner_id, NULL AS equipment_id,"
    " c.contract_number AS code, c.title AS name, NULL AS level, NULL AS lifecycle, s.code AS site_code,"
    " NULL AS unit_code, NULL AS p_code, NULL AS gp_code, NULL AS mf_name, NULL AS m_designation,"
    " NULL AS owner_state, NULL AS action_kind, NULL AS improvement_state"
    " FROM equipment_documents d JOIN contracts c ON c.id = d.contract_id JOIN sites s ON s.id = c.site_id"
)
```

- **Scope:** the site ids where the user holds both `equipment:purge_documents` and
  `contract:read_senior`: `{s["id"] for s in sites_holding(cur, "equipment:purge_documents")} &
  {s["id"] for s in sites_holding(cur, "contract:read_senior")}`. None → the branch is left out
  (not the whole list), as the node branch. Else `c.site_id IN (…)`. Admin: every site.
- **Built with `_scoped_branch`** (one copy of the search and scope SQL): `search_column`
  `CONCAT_WS(' ', c.title, c.contract_number)` (NULL-safe), `unit_column` `c.site_id`, and the site
  ids above as its id list. So `q` matches the title, the number, `d.title` and `d.original_name`.
- **`_removed_item`**, a case of its own: `name` the contract's title, `code` its number (or
  `null`), `unit` the site's code (a contract has no unit; the screen shows it where a unit shows),
  `full_path` `None`, `state` `None`; `path` `/api/contracts/<id>/documents` from `OWNERS`.
- **The screen** (`RemovedDocuments.vue`): "Contract <title>" and under it, small, "<number> · <site>"
  (the number left out when empty). Restore and Delete as every row. Placeholder: "Search equipment
  code, model, ticket, improvement, lesson number, contract, title or file name…".
- IT admin keeps the list (other owners' rows), without contract rows (§ 7 E2).

### 5.6 A PDF with blank lines before its header

**Fact** (checked 30-10-2026, `od -c` on `scratch/AMC14082369550_12606 (1).pdf`): the file starts
`\n\n\n\n\n\n%PDF-1.7`. `detect_file_type` (`backend/documents_core.py:57`) tests
`data.startswith(b"%PDF-")` on the first `SIGNATURE_BYTES` (12) bytes (`backend/documents.py:306`),
so the upload is refused with `TYPE_REFUSED`. The other four real contract PDFs in `scratch/` start
with `%PDF-`.

**The rule (Q1, recommended a):**
- `documents_core.HEADER_WINDOW = 1024`; `_read_upload` calls `detect_file_type(data[:HEADER_WINDOW])`.
- In `detect_file_type`: a PDF when `data.startswith(b"%PDF-")`, or when
  `data.lstrip(b" \t\r\n").startswith(b"%PDF-")` (the whole `%PDF-` inside the window). Any other
  byte before the header (`<html>`, a NUL, text) → `None` (refused). JPEG, PNG and WebP keep their
  exact first-byte rule; leading whitespace before them is refused.
- The stored file keeps its bytes (a signed copy is not altered); it is served with
  `application/pdf` and `nosniff`, as every PDF.
- **Why 1024:** PDF readers look for the header within the first 1024 bytes (Adobe's implementation
  note, PDF Reference 1.7 Appendix H note 13; Chrome's PDFium scans the same 1024 bytes,
  `GetHeaderOffset`; Safari *to verify*, so § 8.5 opens the Fuji file on an Android phone and an
  iPhone).
  Only whitespace is allowed, so no polyglot (HTML or script before the header) passes.
- **Security (self-check 12):** the check runs on the same bytes that are stored and served; the
  served type comes from the check, never from the client.

### 5.7 The contract page (S081's `ContractView.vue`)

- **Place:** after the *Machines covered* card, before any later card.
- **With `can_read_documents`:** one small line, `text-secondary`: "Only the managers of SMTW see
  these documents and photos." (the site's code), then `<DocumentsCards :base-path="docsPath"
  :can-edit="contract.can_edit_documents" />` with `docsPath` = `/api/contracts/${id}/documents`.
  The cards bring their own *Add document* (PDF), *Add photo*, empty states ("No documents yet.",
  "No photos yet."), *Edit title* and *Remove* with its question in the row (`DocumentsCards.vue`,
  unchanged).
- **Without it** (engineers, IT admin, the floor): nothing, as for the price (S081 § 5.4): no card,
  no line, no button. The engineer has the *Covered* / *Not covered* terms.
- **The one-tap path:** *Add document* → choose the PDF → the title is prefilled from the file name
  (`DocumentUploadModal.vue`, unchanged) → *Upload*. On a phone, *Add photo* offers the camera.
- **Destructive:** *Remove* asks in the row ("Remove this document?" Yes / No, unchanged); the
  file stays until a manager erases it in Settings.
- **Disabled controls:** none; a control the user may not use is not shown.

### 5.8 The database or the file store down

Every route goes through `get_db()`: 503 while the database is down (§ Yantra Specifics, *DB may
not exist*). A storage write failure is `STORAGE_UNAVAILABLE` 503 with no file left behind, and a
missing file is the logged 404 "File missing" (`_serve`), unchanged. No background task, no alert.
The NFS share is `DATA_DIR` as a whole (CLAUDE.md § Files), so `contracts/` needs no mount change.

## 6. API

Under `documents_bp` (`/api`), ids `<int:…>`; the same routes, bodies and answers as every owner.

| Route | Key | Answer |
|---|---|---|
| `GET /api/contracts/<id>/documents` | `contract:read_senior` | 200 `{items, upload_max_mb}` (no `inherited`); 403; 404 |
| `POST /api/contracts/<id>/documents` | `contract:edit` (+ `read_senior` at the site) | 201 the item; 400; 403; 404; 503 |
| `GET …/documents/<doc_id>/file`, `…/thumb` | `contract:read_senior` | the file; 403; 404 |
| `PUT …/documents/<doc_id>` | `contract:edit` (+ `read_senior`) | 200 the item; 400; 403; 404 |
| `DELETE …/documents/<doc_id>` | `contract:edit` (+ `read_senior`) | 204; 403; 404 |
| `POST …/documents/<doc_id>/restore` | `equipment:purge_documents` (+ `read_senior`) | 200 the item; 403; 404 |
| `POST …/documents/<doc_id>/purge` | `equipment:purge_documents` (+ `read_senior`) | 204 or 200 `{warning}`; 403; 404; 409 |
| `GET /api/equipment/removed-documents` | `equipment:purge_documents` | rows with `owner` `"contract"` (§ 5.5) |

### 6.1 The contract item (S080 § 6.1, extended)

Two flags, in every answer that holds a contract (`_contract_out`: list, detail, `POST`, `PUT`):
`can_read_documents` = `has_perm_at("contract:read_senior", site_id)`; `can_edit_documents` =
`can_read_documents and has_perm_at("contract:edit", site_id)`. Computed once per site: they are
added to the dict `_SiteFlags.at(site_id)` returns, so every `_contract_out` answer carries them.
They are not gated (always present). The S082 card route (`contracts_for_equipment`) cuts its items
to `_CARD_KEYS`, so the flags never reach the card, and `test_contract_card_api.py`'s exact-item
assert stays green; the list's `sites` array (`can_add`, `can_read_callout`, `can_read_cost` per
site) does not gain them (BS1-05).

## 7. Design decisions

D1–D11 are the roadmap's; this brief's are E1–E7.

- **E1. Write needs `contract:edit` and `contract:read_senior`.** D5 puts every document behind
  `read_senior`; a writer who cannot read would upload blind and could never remove a wrong file. With
  today's roles it is the managers; both keys are checked so a later change to either keeps the
  rule. Rejected: `contract:edit` alone (the roadmap's open point: an engineer uploads a quote and
  then cannot see it, and IT admin could add files to a record it may not read); `read_senior` alone
  as the write key (drops the editor's key from the write path).
- **E2. Restore and erase need `contract:read_senior` too; IT admin is excluded from contract
  documents.** The removed list shows titles and file names, and the restore answers with the item; D5
  and S080 D5 keep IT admin out of the cost. **Departure (stated):** for the other five owners IT
  admin restores and erases (S008, CLAUDE.md § Files). The manager of the site erases contract
  documents; admin by the bypass. Rejected: IT admin as for every owner (shows a quote's title such
  as "Fuji AMC quote ₹28,028" to a role D5 keeps from prices).
- **E3. The three functions live in contracts.py, documents.py imports them**, as `read_action` and
  `read_procedure` (S070, S075). Rejected: the checks inside documents.py (the contract's rules in
  two modules).
- **E4. No state rule.** § 5.3. Rejected: refusing an inactive contract (S081 refuses *Add machine*
  there): a contract entered by mistake may still need its paper removed, and one function then
  serves every write, as the model's and the lesson's.
- **E5. Leading whitespace before `%PDF-` accepted, for every owner** (Q1). One check for one file
  type; the Fuji quote is the first real case. Rejected: a contract-only rule (one file accepted on
  a contract and refused on a machine); asking the manager to re-save the PDF (a phone has no tool
  for it).
- **E6. A quote shared by two contracts is uploaded to each** (D7's Fuji case). Each owner has its
  own folder, and the CHECK holds one owner per row. Rejected: a link table for shared documents (a
  new design for two rows a year).
- **E7. Two flags in the item, not the page reusing `can_read_cost`.** The same key today, but the
  page states what it shows. Rejected: `v-if="contract.can_read_cost"` (ties documents to the cost
  field's name).

## 8. Tests and acceptance

### 8.1 Migration (`backend/tests/test_migration_v45.py`)

`V44 = … range(20, 45)`, `V45 = … range(20, 46)`, `VERSIONS = list(range(20, 46))`; helpers from
`test_migration_v20` (`_migrate`, `_recreate`, `_run`, `_schema`), `test_migration_v36` (`_keys`,
`_foreign_keys`), `test_migration_v38` (`_owner_check_clause`, `_add_document`) and v41's row
helpers; a contract row inserted by SQL (a vendor, then a contract at the one site).
- `test_a_fresh_database_gets_v45`: the column (nullable, after `procedure_id`), the key, the foreign
  key to `contracts`; `contract_id` in the CHECK clause.
- `test_a_v44_database_keeps_every_row`: documents of the five owners kept, `contract_id` NULL.
- `test_a_document_has_exactly_one_of_six_owners`: a contract document alone accepted; with
  `procedure_id` also set → 4025.
- `test_a_rerun_changes_nothing` (`_schema()` equal); `test_a_half_applied_v45_adds_the_owner_check_again`.

### 8.2 Backend

**`test_documents_core.py`**, `TestDetectFileType`: `test_blank_lines_before_a_pdf_header_are_accepted`
(`b"\n" * 6 + PDF_HEAD`, `b" \r\n\t" + PDF_HEAD`, refused `b"\f" + PDF_HEAD`, `b"\n" * 1019 + b"%PDF-"`) and
`test_other_bytes_before_a_header_are_refused` (`b"<html>" + PDF_HEAD`, `b"\x00" + PDF_HEAD`,
`b"\n" * 1020 + b"%PDF-1.7"` cut at 1024, `b"\n" + JPEG_HEAD`, `b" " + PNG_HEAD`).

**`test_documents_api.py`**: `TestUploadAndServe::test_a_pdf_with_blank_lines_before_its_header_is_stored_as_it_is`
(a node document `b"\n" * 6 + PDF`: 201, `content_type` `application/pdf`, the file served byte for
byte). `TestOwnerCheckConstraint::test_a_lesson_and_a_contract_together_are_refused` (4025).
**`TestContractDocuments`**, fixture `contract_case` (`make_site` twice, `make_vendor`, a contract at
the first site by the admin's `POST /api/contracts`, clients by `user_at_sites`: manager, engineer,
operator at the site, manager of the other site; IT admin by `role_client("it_admin")`):
- `test_the_manager_uploads_lists_and_opens`: 201; `contract_id` stored, the other owner columns NULL;
  the files under `DATA_DIR/contracts/<id>/` (`owner_files("contract", id)`); list 200 without
  `inherited`; file 200 with `nosniff` and `private`; a photo gets its thumb.
- `test_an_engineer_it_admin_and_an_operator_neither_read_nor_write`: list 403, file 403, upload 403
  with no file written, for each.
- `test_a_manager_of_another_site_gets_404`: list, file, upload.
- `test_an_engineer_here_who_is_manager_elsewhere_is_refused_here`: passes `_owner_key` (holds
  `read_senior` elsewhere), list 403 and upload 403 at this site.
- `test_retitle_and_remove`; `test_an_inactive_and_an_ended_contract_take_documents` (201 each).
- `test_a_document_of_another_contract_and_an_unknown_contract_are_404`.
- `test_admin_reads_and_writes` (the bypass).
- `test_the_database_down_is_503` (`db_down`, `backend/tests/conftest.py`): the list answers 503.

**`test_removed_documents_api.py`**, **`TestContractRows`**:
`test_listed_with_the_title_number_and_site` (`owner` `"contract"`, `name`, `code`, `unit` = the
site's code, `state` `None`, `path`); `test_q_matches_the_title_and_the_number`;
`test_only_the_sites_manager_sees_them` (IT admin: no contract rows; a manager of another site: none);
`test_restore_and_purge_by_the_manager` (200, then 204 and the files gone);
`test_it_admin_may_not_restore_or_purge` (403).

**`test_contracts_api.py`** (from S080): `test_the_document_flags_follow_the_keys` (manager: both
true; engineer and IT admin: both false; admin: both true; the keys present on the list item and the
detail).

### 8.3 Existing tests that break or run again

- `backend/tests/test_contracts_api.py` (from S080): any test that compares an item's whole key set
  gains `can_read_documents` and `can_edit_documents`. Checked (s1): it asserts the flags as tuples
  of named keys (lines 84, 98, 105), never a whole key set, so nothing breaks.
- `backend/tests/test_removed_documents_api.py`: `TestList::test_the_unit_scope_is_enforced_fail_closed`
  runs again and stays green: its `nobody` is an engineer, who holds no `contract:read_senior`, so the
  contract branch is left out and the last line (`item["owner"] in ("model", "procedure")`) holds.
  `TestList::test_who_may_list`: green (the route key is unchanged).
- `backend/tests/test_documents_api.py`: `TestOwnerCheckConstraint`'s three tests green (the CHECK
  keeps its name); `TestUploadRefusals` green (its refused bytes have no whitespace prefix; the coder
  checks each case against § 5.6).
- `backend/tests/test_documents_core.py::TestDetectFileType::test_anything_else_is_none`: green (none
  of its cases starts with whitespace then `%PDF-`).
- `backend/tests/test_migration_v12.py`, `test_migration_v38.py`, `test_migration_v41.py`: green (each
  slices its own range).
- `backend/tests/test_modules.py`: reads `LATEST_VERSION`, now 45; green.
- `backend/tests/test_rbac.py::test_role_matrix`: unchanged (no new key).
- `backend/tests/conftest.py`: no change (`equipment_documents` is in `_TABLES`; no new table).

### 8.4 Automated (e2e, `frontend/e2e/contracts.spec.js`)

Set-up by API with S080's in-spec helpers (a vendor, a contract at SMTW); each test makes its own
contract, so no count depends on another test.
- `S083: a manager adds the signed contract as a PDF and sees it in Documents` (untagged): as the
  manager, open `/contracts/<id>`, the line "Only the managers of SMTW see these documents and
  photos.", *Add document* → `expectDialogFits` → `test-manual.pdf`, title "Signed contract" →
  *Upload*; the *Documents* card shows "Signed contract" and "test-manual.pdf".
- `S083: a manager removes a contract document and restores it from Settings` (untagged): upload by
  API, *Remove* → Yes; Settings › Removed documents, search the contract's title: the row "Contract
  <title>" with "SMTW"; *Restore*; the contract page shows the document again.
- `S083: an engineer sees no Documents card on the contract page` (untagged): as the engineer, no
  `"Add document"` button and no *Documents* card header.

Targeted runs: `tooling/run-e2e-tests.bat e2e/contracts.spec.js e2e/settings.spec.js
e2e/equipment.spec.js e2e/screens.spec.js` (equipment for the shared upload path); the whole suite
at Normal once at the end (`documents.py` serves every documents screen). No shared frontend file
changes (settings: *Shared code*).

### 8.5 On a real device

One row for `docs/steps/device-checks.md`, **important**: "On an **Android phone** and on an
**iPhone**, as a manager (dev server), open a contract, tap **Add document**, choose the Fuji quote
PDF from **Files** (KLA puts a copy of `AMC14082369550_12606 (1).pdf` on each phone), *Upload*. Tap
its title: the PDF opens in the phone's viewer and its pages show (the file starts with blank
lines, § 5.6)." Account: a manager's login at SMTW (dev server: none). Network: company Wi-Fi or
home network. Where: dev server (the quote holds a real price; not on production). A browser
engine cannot judge the phone's file picker or its PDF viewer; the camera path of `DocumentsCards`
is already checked on real phones (rows 5, 46, 51, 56).

### 8.6 Acceptance

- All unit suites green; `tooling\schema-docs.bat check` exits 0; the whole browser suite at Normal
  green once.
- By API: the manager of SMTW attaches the Fuji quote (with its blank lines) and a photo to an AMC;
  the engineer and IT admin get 403; IT admin's removed list shows no contract row.
- The device row done or skipped by KLA.

## 9. Open questions and assumptions

- **Q1. Accept a PDF with whitespace before its header?** (§ 5.6, E5)
  - **(a) Yes, only spaces, tabs and line breaks, within 1024 bytes, for every owner — recommended.**
    The real Fuji quote uploads; nothing but whitespace may precede the header.
    Taken as recommended by the orchestrator under the delegation of 30-10-2026; KLA may override
    at gate B.
  - (b) No: the manager re-saves the file on a computer (print to PDF) before upload. No change to
    the type check; the phone path fails for this file.
- **Roadmap corrections** (for the orchestrator): R02.3's "After it: the engineer finds the contract
  from a phone" contradicts D5 (documents for managers only): it is the manager. R02.3 says "a
  `contract:read_basic` holder sees no documents", which holds for `contract:read` holders too. *What
  exists* names only v38 as having widened the CHECK; v41 did too (`backend/local_db.py`, the v41
  entry).
- **Checked (s1):** `auth_utils.sites_holding` exists as S082 states; documents.py imports it.
- **Checked (s1):** S080 builds the flags in one place, `_SiteFlags.at`, so the two new flags reach
  every `_contract_out` answer from there.
- **Assumption:** S081's page has no documents placeholder (S081 B8), so S083 adds the cards, not
  replaces one.
- **E1 (write needs `contract:edit` and `contract:read_senior`):** taken as recommended by the
  orchestrator under the delegation of 30-10-2026; KLA may override at gate B.
- **E2 (IT admin does not restore or erase contract documents):** a departure from S008's rule
  that IT admin restores and erases every owner's removed documents (`.claude/CLAUDE.md` § Files).
  Taken as recommended by the orchestrator under the delegation of 30-10-2026; KLA may override at
  gate B.
- **Staleness check due before coding:** S084's contract lock note (`alerts.lock_contract_for_scan`), the migration number (v45; S084 may take v46), the LOCK
  ORDER bullets of S080 and S081, `_contract_out`, `sites_holding`, `ContractView.vue`.
- **No defining question.** Q1 is a judgement on the upload check; both answers are safe.

## 10. Amendments

None.

## Review log

### Round 1 — `2-brief-review-r1.md` (Fable), answered 30-10-2026

| Finding | Answer |
|---|---|
| BR1-01 (minor) Q1 and E2 not marked as taken under the delegation | Accepted: § 9 marks Q1 (a), E1 and E2 "Taken as recommended by the orchestrator under the delegation of 30-10-2026; KLA may override at gate B"; E2 names its departure from S008's IT-admin rule. |
| BR1-02 (minor) the line for users who may not read the documents | Accepted (a): a non-holder sees nothing (§ 5.7); the third e2e test asserts only no *Documents* card and no `"Add document"`. |
| BR1-03 (minor) the device row: no iPhone, a camera check already done | Accepted (a): one row, Android and iPhone both open the Fuji PDF on the dev server; the camera half dropped (§ 8.5). |
| BR1-04 … BR1-10 (nits) | Accepted as recommended: one whitespace set (`\f` dropped, now refused); `SIGNATURE_BYTES` leaves documents.py's imports; `read_contract` selects `id, site_id`; "the manager's way"; the contract branch through `_scoped_branch`; S084's scan lock in § 5.4 and the staleness list; S082's `/for-equipment/<int:node_id>` named. The ISO 27001 numbers A.5.15, A.8.3, A.8.10 confirmed; their "to verify" dropped. |

### Staleness s1 — `2-brief-review-s1.md` (Fable), answered 31-10-2026

| Finding | Answer |
|---|---|
| BS1-01 (minor) S080's planned names, not the coded ones | Accepted: § 3 names `_contract_row`, `_lock_contract`, `_contract_out(row, flags, today)` and `_SiteFlags.at` with its three flags; § 3 Backend and § 6.1 add the two flags to the dict `_SiteFlags.at` returns; § 9's `_sites_holding` fallback replaced by "checked". |
| BS1-02 (minor) S081's lock-note sentences become false | Accepted: § 5.4's "The coder writes" list gains the first bullet's documents path and the node (1) bullet's two-path sentence. |
| BS1-03 (minor) `lock_contract_for_change` duplicates `_lock_contract` | Accepted (a): `_lock_contract` gains a `key` parameter; `lock_contract_for_change` is it plus the `read_senior` check (§ 5.1); `_contract_access` serves the plain reads only. |
| BS1-04 … BS1-09 (nits) | Accepted: `_PRECONDITIONS` anchor `:1589`; § 6.1 names the card route's `_CARD_KEYS` and the `sites` array; § 8.3's first bullet now checked; the ACCESS docstring paragraph in § 3 Backend; the CLAUDE.md sentence replaced, not appended; BS1-09 needs no change (`make_vendor`'s caller does not matter for `contract_case`). |
