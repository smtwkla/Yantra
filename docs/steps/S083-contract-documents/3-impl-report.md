```
Step: S083 — Contract documents
Doc: impl report
Author: Coder (Opus)
Date: 31-10-2026
```

# S083 — implementation report

**S083 is built as the brief says, with no departure.** The unit suites are green: backend 4387, frontend
397, tooling 231. The schema docs check exits 0 and the build passes. The whole browser suite at Normal has
348 passed, 15 skipped and 2 failed; the 2 failures are the known S048 changelog fault outside this step.

## 1. What was built

- **The contract is the sixth documents owner.** A manager uploads, lists, opens, downloads, retitles and
  removes a contract's documents (PDF) and photos at `/api/contracts/<id>/documents`, through the existing
  routes of `backend/documents.py`. The files live in `DATA_DIR/contracts/<id>/`.
- **Every route is behind `contract:read_senior` at the contract's site** (D5). Write needs `contract:edit`
  and `read_senior` there (E1). Restore and erase need `equipment:purge_documents` and `read_senior` there
  (E2). So the site's managers do all of it; engineers, IT admin and the floor do none of it; admin all.
- **The contract page** (`ContractView.vue`) shows the line "Only the managers of SMTW see these documents
  and photos." and the shared *Documents* and *Photos* cards after *Machines covered*, only for
  `can_read_documents`. Their buttons follow `can_edit_documents`. Others see nothing of them.
- **Settings › Removed documents** lists a removed contract document as "Contract <title>", with
  "<number> · <site>" under it (the number left out when empty). Restore is never disabled for it.
- **A PDF with blank lines before its header is accepted, for every owner** (Q1 a). Spaces, tabs, `\r` and
  `\n` may come before `%PDF-` inside the first 1024 bytes. Any other byte before it is refused. The
  stored file keeps its bytes.
- **Migration v45**: `equipment_documents.contract_id` with its key and foreign key, and the owner CHECK
  widened to six columns.
- **Two flags on every contract item**: `can_read_documents`, `can_edit_documents`.

## 2. How it works

- **contracts.py** gains three functions for documents.py's `Owner` slots:
  - `read_contract(cur, id)`: a plain `SELECT id, site_id`, then `_contract_access`: 404 without
    `contract:read_basic` at the site, 403 without `read_senior` there.
  - `read_contract_for_change(cur, id, key)`: the same, then `key` at the site (403). A refused upload
    reads and writes no file.
  - `lock_contract_for_change(cur, id, key)`: S081's `_lock_contract(cur, id, key)` (now with a `key`
    parameter, default `contract:edit`, so the line writes are unchanged), then `read_senior` at the
    locked row's site (403). It serves change and purge: no state rule.
- **`_SiteFlags.at`** adds `can_read_documents` (= `can_read_cost`, the same key) and `can_edit_documents`
  (`read_senior` and `edit`). `_contract_out` copies the flags into every item, so the list, the detail
  and every write's answer carry them. The card route still cuts its items to `_CARD_KEYS`, and the list's
  `sites` array is unchanged.
- **documents.py**: `OWNERS["contract"]` names the three functions and the keys `contract:read_senior`,
  `contract:edit`, `equipment:purge_documents`. A sixth stacked decorator (`_CONTRACT_DOCS`,
  `_FOR_CONTRACT`) sits on each of the eight routes. The route's `_owner_key` checks the key held at any
  site; the contract functions then check at the contract's site.
- **The removed list**: `_REMOVED_CONTRACT_BRANCH` joins the contract and its site. `_removed_branches`
  adds it through `_scoped_branch`, scoped to the sites in both `sites_holding(cur,
  "equipment:purge_documents")` and `sites_holding(cur, "contract:read_senior")`, and leaves it out when
  there are none. `q` searches `CONCAT_WS(' ', c.title, c.contract_number)`, the title and the file name.
  `_removed_item` sets `unit` to the site's code and `full_path` and `state` to `None`.
- **The PDF rule**: `documents_core.HEADER_WINDOW = 1024`. `_read_upload` passes `data[:HEADER_WINDOW]`.
  `detect_file_type` cuts its input to the window, then tests
  `data.lstrip(b" \t\r\n").startswith(b"%PDF-")`. JPEG, PNG and WebP keep their exact first-byte tests, so
  whitespace before them is refused.
- **Locks**: a document write on a contract takes one owner lock, the contract row `FOR UPDATE`, first
  in its transaction, then touches only `equipment_documents` rows. The notes in contracts.py,
  equipment.py and documents.py say so, with the sentences of brief § 5.4.

## 3. Files touched

| File | Change |
|---|---|
| `backend/local_db.py` | Migration v45 (three statements) with its comment. |
| `backend/contracts.py` | `_lock_contract` gains `key`; `_contract_access`, `_contract_site`, `read_contract`, `read_contract_for_change`, `lock_contract_for_change`; the two flags in `_SiteFlags.at`; the ACCESS and LOCK ORDER notes. |
| `backend/documents.py` | `OWNERS["contract"]`, `_CONTRACT_DOCS`, `_FOR_CONTRACT`, the eight decorators, `_REMOVED_CONTRACT_BRANCH`, its case in `_removed_item` and `_removed_branches`, `HEADER_WINDOW` in `_read_upload`, `SIGNATURE_BYTES` out of the imports, the module docstring. |
| `backend/documents_core.py` | `HEADER_WINDOW`, the leading-whitespace PDF rule in `detect_file_type`. |
| `backend/file_store.py` | `"contract": "contracts"` in `_OWNER_FOLDERS`; the layout line. |
| `backend/equipment.py` | Docstring only: the documents.py and contracts.py bullets of LOCK ORDER. |
| `frontend/src/views/ContractView.vue` | The line and `DocumentsCards` after *Machines covered*, for `can_read_documents`; the docstring. |
| `frontend/src/views/settings/RemovedDocuments.vue` | The contract cell, the placeholder, the docstring. |
| `backend/tests/test_migration_v45.py` | New: five tests (§ 8.1). |
| `backend/tests/test_documents_core.py` | The whitespace cases in `TestDetectFileType`. |
| `backend/tests/test_documents_api.py` | The blank-lines PDF test, the six-owner CHECK test, `TestContractDocuments` with `contract_case`. |
| `backend/tests/test_removed_documents_api.py` | `TestContractRows`. |
| `backend/tests/test_contracts_api.py` | `test_the_document_flags_follow_the_keys`. |
| `frontend/e2e/contracts.spec.js` | The three S083 tests and their helpers; the header comment. |
| `docs/schema/notes.json`, `schema.json`, `schema-data.js` | The sixth owner; regenerated. |
| `docs/Plan.MD`, `.claude/CLAUDE.md`, `docs/steps/device-checks.md` | The docs pass (below). |

## 4. Decisions taken

No departure from the brief. Small choices:
- **`_contract_site(cur, id)`**, a private helper for the one plain `SELECT id, site_id FROM contracts`,
  shared by the two plain reads (no copy). `_contract_row` was not reused: it selects every column and
  joins the line sums, more than an access check needs.
- **`detect_file_type` cuts its input to `HEADER_WINDOW` itself**, as well as `_read_upload` passing the
  window. So the core alone decides the rule, and the test case `b"\n" * 1020 + b"%PDF-1.7"` is refused
  whole or cut.
- **`can_read_documents` is computed from the same `has_perm_at` call as `can_read_cost`** (one call per
  site), as E7 asks for a flag of its own name.
- **`DocumentsCards` gets `:key="contract.id"`**, so moving from one contract page to another loads the
  new contract's documents.
- **The removed-list scope for admin** is the list of every site that `sites_holding` returns (the bypass
  passes every site), not a `None` "every site": one code path, the same rows.
- **The contract cell in Removed documents** has `text-break`, since a contract title is up to 100
  characters.
- **The test of IT admin's restore** also asserts a manager of another site gets 404 (404 before 403).

## 5. Not done, deferred or assumed

- **Known fault outside the step:** the 2 S048 changelog tests (`e2e/changelog.spec.js:14`,
  desktop-chromium) fail because `CHANGELOG.md` has an empty 0.1.14 section. Left alone, as asked.
- **Schema docs:** `schema.json` was at migration 41 before this step's write; the write took it to 45, so
  the diff also holds S079–S082's tables (`vendors`, `contracts`, `contract_equipment`, the `people`
  vendor link, the history kinds). Those come from the migrations as they are; nothing was edited by hand.
- **Safari's PDF viewer** with blank lines before the header is not checked by a browser test; device row
  60 checks it on an iPhone and an Android phone (brief § 5.6, § 8.5).
- The 403 order on the locked path (`key` before `read_senior`) differs from the plain path, as BS1-03
  accepted; both answer the same message.

## Manual checks

- [auto] A manager adds the signed contract as a PDF and sees it in Documents — `frontend/e2e/contracts.spec.js`::`S083: a manager adds the signed contract as a PDF and sees it in Documents`
- [auto] A manager removes a contract document and restores it from Settings — `frontend/e2e/contracts.spec.js`::`S083: a manager removes a contract document and restores it from Settings`
- [auto] An engineer sees no Documents card on the contract page — `frontend/e2e/contracts.spec.js`::`S083: an engineer sees no Documents card on the contract page`
- [ ] **Important.** On an Android phone and on an iPhone, as a manager (dev server), add the Fuji quote PDF
  from Files to a contract, then tap its title: the PDF opens in the phone's viewer and its pages show.
  Device-check row 60.

## Tests run

All with `YANTRA_TEST_RUN=s083c1`.

| Run | Result |
|---|---|
| Targeted backend: `test_documents_core.py`, `test_migration_v45.py`, `test_migration_v41.py` | 68 passed |
| Targeted backend: `test_documents_api.py`, `test_removed_documents_api.py`, `test_contracts_api.py`, `test_contract_card_api.py`, `test_contract_equipment_api.py`, `test_documents_core.py` | 268 passed (first run) |
| New browser tests alone: `E2E_LANES=1`, `e2e/contracts.spec.js --project=phone-chromium -g S083` | 3 passed |
| Targeted browser (Normal): `e2e/contracts.spec.js e2e/settings.spec.js e2e/equipment.spec.js e2e/screens.spec.js` (the changed screens, the shared upload path, the settings card, plus screens) | 105 passed, 2 skipped |
| `tooling/run-tests.bat` (once, at the end) | backend 4387 passed, frontend 397 passed, tooling 231 passed |
| `npx vite build` in `frontend/` | built; only the known chunk-size warning |
| `tooling/schema-docs.bat write`, then `check` | 4 passed, migration 45; check exit 0 |
| Whole browser suite at Normal (`tooling/run-e2e-tests.bat`, once) | 348 passed, 15 skipped, 2 failed: `e2e/changelog.spec.js:14` on desktop-chromium, both S048 tests (it_admin, admin), the known fault (empty 0.1.14 section in `CHANGELOG.md`); 184 s |

No red full run, so no repeat.

## Docs updated

- `docs/schema/notes.json`: the `equipment_documents` line names the sixth owner (`contract_id`, S083, v45,
  its index) and "the six columns". Then `tooling\schema-docs.bat write` (4 passed, migration 45),
  `git diff docs/schema/` read, `check` exit 0.
- `docs/schema/schema.json`, `docs/schema/schema-data.js`: generated by the write, not edited.
- `docs/Plan.MD`: § 2 item 9, the sentence on the attached documents; § 3, the contract keys' paragraph:
  the documents rule and IT admin's exclusion (E2).
- `.claude/CLAUDE.md`: § Yantra Specifics, *Files (S006)*: six owners, the sixth the contract; § SMTW-Review,
  *Contract fields by key*: "R02.3's documents join this rule." replaced by the S083 documents rule.
- `docs/steps/device-checks.md`: row 60 (§ 8.5).
- `docs/Keycloak.md`: none, because no role, client or claim changed.
- `backend/example_secrets_app.py`: none, because no secret was added.

## Fix rounds

### Round 1

- **CR1-01 (minor): Fixed.** `docs/schema/notes.json`, the `equipment_documents` line now ends "... by the
  manager or IT admin from Settings (S008); a contract's only by the site's manager (S083 E2)".
  `tooling\schema-docs.bat write` (migration v45, 4 passed), then `check`: PASSED (4 passed).
  `schema-data.js` followed; the diff is unchanged in size (228 lines, as before). No test covers a doc line,
  so no red run applies.
- **CR1-02 (nit): Fixed.** `contracts._contract_access(row, key)` no longer takes `cur`; its two callers
  (`read_contract`, `read_contract_for_change`) are updated. No test calls it. A pure signature change, so no
  red run applies.

Tests (`YANTRA_TEST_RUN=s083c2`): `tooling/run-backend-tests.bat tests/test_contracts_api.py
tests/test_documents_api.py tests/test_removed_documents_api.py`: 162 passed. Schema docs check: 4 passed.
No browser run: no screen changed.

Docs updated: `docs/schema/notes.json` (by hand), `docs/schema/schema.json` and `docs/schema/schema-data.js`
(generated by the write). No other doc is due.

### Feedback (round 1)

- none

## Feedback

- waste: seven Edit calls failed with "File has not been read yet": six on files I had only seen through
  `grep`/`sed` in Bash, and three on this report right after the Write tool had created it (the file had
  changed on disk, probably the IDE); each needed a Read first (about 3 min).
- idea: the brief's *Docs* list could say when the step's schema write also takes in earlier open steps'
  migrations (here `schema.json` went from v41 to v45, S079–S082 included), so the coder and the reviewer
  expect the larger `docs/schema/` diff (`git diff --stat docs/schema/`: 228 lines for a one-column change).
