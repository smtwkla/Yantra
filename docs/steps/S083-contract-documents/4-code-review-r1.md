```
Step: S083 — Contract documents
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 31-10-2026
```

# S083 — code review, round 1

**Verdict: no `blocker` or `major` finding is open.** One `minor` finding (a doc line the change makes
wrong) and one nit. The code matches the brief, its staleness answers and the impl report's
"Decisions taken". All three unit suites are green. The schema docs check exits 0, and the build passes.

## Tests run

All runs used `YANTRA_TEST_RUN=s083cr1`.

| Run | Result |
|---|---|
| `tooling/run-tests.bat` | backend 4387 passed (245 s), frontend 397 passed, tooling 231 passed; ALL SUITES PASSED |
| `tooling/schema-docs.bat check` | migration v45, 4 passed, exit 0 |
| `npx vite build` in `frontend/` | built; only the known chunk-size warning |
| Browser tests | none re-run: no finding of mine needs one. I rely on the coder's runs: targeted Normal on `contracts`, `settings`, `equipment` and `screens` (105 passed, 2 skipped), and the whole suite at Normal once (348 passed, 15 skipped, 2 failed; both failures are the known S048 changelog fault, `e2e/changelog.spec.js:14`, outside S083). These are the right specs: brief § 8.4 names them, and the step changes no shared frontend file. |

## Findings

### CR1-01 (minor) `docs/schema/notes.json:19`: the `equipment_documents` line still says IT admin restores every removed document

- **Problem.** The coder edited this line for the sixth owner. Its end still says "a removed document is
  restored or deleted for good … by the manager or IT admin from Settings (S008)". Since S083 (E2) this
  is false for a contract's documents: IT admin neither sees nor restores them.
- **Failure scenario.** A later brief or the `/smtw-review` audit reads the schema page for "who may
  restore a document". It concludes that IT admin can restore a contract quote, which is the case E2
  rules out.
- **Fix.** End the sentence with "… by the manager or IT admin from Settings (S008); a contract's only
  by the site's manager (S083 E2)". Then run `tooling\schema-docs.bat write`, so `schema-data.js` follows.
  The `check` must exit 0.

## Nits

- **CR1-02** (nit) `backend/contracts.py:538`: `_contract_access(cur, row, key)` never uses `cur`. Drop
  the parameter, or keep it and say why in the docstring (for example, to match the brief's signature).

## Checked and found consistent

- **Every route needs `contract:read_senior` at the contract's site.**
  - `read_contract` and `read_contract_for_change` reach `_contract_access`: 404 without `read_basic`,
    then `require_perm_at(READ_COST)`.
  - `lock_contract_for_change` checks `require_perm_at(READ_COST, locked["site_id"])` after
    `_lock_contract(cur, id, key)`. Restore and purge pass through it with `equipment:purge_documents`
    as `key`.
  - List, file and thumb use `read`. Upload uses `read_for_change`, then the lock. PUT, DELETE, restore
    and purge use the lock alone.
  - `READ_COST` is `"contract:read_senior"` (`contracts.py:93`).
  - The tests cover the locked path's own `read_senior` check. The engineer holds `contract:edit`, so
    in `test_retitle_and_remove` the PUT and DELETE pass `_lock_contract` and are refused by
    `read_senior`. IT admin's restore and purge in `TestContractRows` show the same for the purge key.
- **IT admin sees no contract document (E2).**
  - Upload, list and file are 403 (`test_an_engineer_it_admin_and_an_operator_neither_read_nor_write`).
  - Restore and purge are 403.
  - The removed list shows no contract row: the scope is the intersection of `sites_holding` for the
    purge key and for `read_senior`, which is empty for IT admin, so the branch is left out
    (`test_only_the_sites_manager_sees_them`).
  - The page shows no card, because `can_read_documents` is false.
- **Lock order.**
  - Every document write takes the contract row `FOR UPDATE` first in its transaction. Then it touches
    only `equipment_documents` rows. The insert's foreign-key shared lock falls on the row already held.
  - The LOCK ORDER notes carry the sentences of brief § 5.4 and BS1-02:
    - in `contracts.py`: the documents bullet, the first no-cycle bullet and the node (1) sentence;
    - in `equipment.py`: the documents.py and contracts.py bullets;
    - in the `documents.py` docstring: the *Locks* paragraph.
  - S084's scan lock does not exist yet (`alerts.py` has no `lock_contract_for_scan`), so nothing more
    is needed now.
- **`_lock_contract`'s new `key` parameter.** It defaults to `EDIT`. The three line writes
  (`contracts.py:489, 509, 525`) still call it with two arguments, so their behaviour is unchanged. The
  S081 suites are green in the full run.
- **Migration v45.** It has three statements, as in brief § 4.1, with `IF NOT EXISTS` and `DROP …
  IF EXISTS`, and the foreign key has no `ON DELETE`. No `_PRECONDITIONS` entry is needed, and I
  confirm this. The change adds a nullable column, a key and a foreign key that no row uses. The new
  CHECK holds for every existing row, because v41's CHECK already keeps each row to exactly one of the
  five owners and `contract_id` is NULL. Nothing is converted or dropped. `test_migration_v45.py` runs
  v45 on a v44 database with documents of all five owners and a contract. It also covers the re-run
  and the half-applied case. `schema-docs check` exits 0 at v45.
- **The PDF whitespace rule.**
  - `detect_file_type` cuts its input to `HEADER_WINDOW` (1024), then tests
    `lstrip(b" \t\r\n").startswith(b"%PDF-")`. Only space, tab, CR and LF may come first, and the whole
    `%PDF-` must sit inside the window.
  - JPEG, PNG and WebP keep their first-byte tests. `_read_upload` is the only caller
    (`git grep detect_file_type`), so the rule holds for every owner.
  - A non-PDF cannot pass. Any other byte before the header gives `None`, and a whitespace-only head
    has no `%PDF-`.
  - The tests cover the boundary: 1019 LF plus `%PDF-` is accepted; 1020 LF plus `%PDF-1.7` is refused,
    cut or whole. They also refuse `\f`, `<html>`, NUL, and whitespace before JPEG or PNG.
  - The stored bytes are served unchanged, as `application/pdf` with `nosniff`
    (`test_a_pdf_with_blank_lines_before_its_header_is_stored_as_it_is`).
- **Files served only through checked routes.** `_serve` calls `_owner_key` and then `OWNERS[owner].read`
  before `send_file`, and the answer is `private`. `file_store._OWNER_FOLDERS` gains `contracts`, and
  no static route serves `DATA_DIR`.
- **The small choices in "Decisions taken".**
  - `_contract_site` is shared by the two plain reads, with no copy. `_contract_row` would read too much.
  - The double cut to the window is harmless and lets the core decide alone.
  - `can_read_documents` reuses the `can_read_cost` call, with a flag of its own name (E7).
  - `:key="contract.id"` on `DocumentsCards` reloads the list on a contract change. Its sibling key on
    `ContractMachineDialog` sits in a different fragment, so the keys do not clash.
  - The removed-list scope for admin uses `sites_holding`'s every site, which gives the same rows.
  - `text-break` on the contract cell suits a 100-character title.
  - The extra 404 assert follows the rule "404 before 403".
- **Flags.** `_SiteFlags.at` carries both flags, so the list, the detail, POST and PUT carry them. The
  card route still cuts to `_CARD_KEYS`, and the list's `sites` array is unchanged (§ 6.1, BS1-05).
- **The removed list.** `_REMOVED_CONTRACT_BRANCH` has the columns of every branch, in their order, and
  is built with `_scoped_branch`. `q` searches `CONCAT_WS(' ', c.title, c.contract_number)`, the title
  and the file name. `_removed_item` gives `unit` the site code and `state` `None`. Restore is never
  disabled for a contract row (`restoreBlocked` has no contract case).
- **Security.** No actor comes from the client (`actor()`), and every SQL is parameterised. The site
  ids go in as `%s` marks. The 503 for a database that is down is tested (`db_down`).
- **Design.** The contract's rules live in contracts.py, and documents.py imports them (E3). The pure
  rule lives in `documents_core`. The Vue files are presentational. Nothing repeats an existing helper.
- **Floor use (UX).**
  - The cards and buttons show only with the flags, so no button ends in a 403.
  - *Remove* asks in the row ("Remove this document?").
  - The line "Only the managers of SMTW see these documents and photos." is short and plain.
  - The upload dialog is the shared `DocumentUploadModal`, and the e2e test calls `expectDialogFits`
    on it.
  - No new error string reaches the user: `TYPE_REFUSED` is unchanged.
- **The browser tests.** Each *Automated* check of § 8.4 has a test that asserts what the user sees:
  - the line, the empty state, and the title and file name in the card;
  - the removed row "Contract <title>" with "SMTW", the "Restored …" toast, and the document back on
    the page;
  - for the engineer: no button, no card header and no line.

  All three are untagged, which is right: they are logic tests.
- **The docs pass.**
  - `.claude/CLAUDE.md` § Files (six owners) and the § SMTW-Review sentence are replaced.
  - `docs/Plan.MD` § 2 item 9 and § 3's contract paragraph cover the rule and E2.
  - `notes.json` is updated and regenerated; CR1-01 is the one line left wrong.
  - `device-checks.md` has row 60.
  - `docs/Keycloak.md` and `example_secrets_app.py` need no change: no role or secret changed.
- **Manual checks.** The impl report's `## Manual checks` holds the three `[auto]` checks with their
  tests and the important device check as an unticked box (row 60).
- **Scope.** Everything in brief §§ 3–8 is built. Nothing extra is built, and no departure is unreported.

## Manual browser checks still open for the user

- [ ] **Important** (device-check row 60): on an Android phone and on an iPhone, as a manager on the
  dev server, add the Fuji quote PDF `AMC14082369550_12606 (1).pdf` from **Files** to a contract. Then
  tap its title: the PDF opens in the phone's viewer and its pages show. The file starts with blank
  lines, and Safari's handling of them is not verified.

## Feedback

- hindrance: my first `step_snapshot.py diff S083 -- …` named `.claude/CLAUDE.md` and `docs/Plan.MD`.
  Their one-line paragraphs pushed the output to 58 KB, so it was saved to a file, and I ran the diff
  again without them (1 extra run, about 1 min).
