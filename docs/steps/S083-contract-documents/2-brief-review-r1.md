```
Step: S083 — Contract documents
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 30-10-2026
From: R02.3
```

Reviewed against: d216f48 + uncommitted S079 (S080–S082 are approved and not coded; their names were
checked against their briefs, not code)

# S083 — Brief review, round 1

**Verdict: no blocker or major finding is open.** Three minor findings and seven nits. Facts file
read: `scratch/brief-facts-S083.md`; every existing name, line and route it lists checked out, and the
"not found" names are the ones S080–S082 define. The sixth owner follows the five existing ones
exactly (the `Owner` tuple, the stacked route decorators, the removed-list branch shape, the folder).
The change to the PDF header check does not weaken the type check (the reasons are in *Checked and
found consistent*).

## For KLA's own decision (gate A is delegated tonight)

Three points in this brief are judgement calls, not forced moves. The brief states them; it does not
mark them as taken under the delegation, as S080 and S081 did (BR1-01):

1. **Q1 (a)** — a PDF with only whitespace before `%PDF-` is accepted, for **every** owner. Safe (see
   below), but it changes the shared type check of S006, not only the contract's.
2. **E2** — IT admin may **not** restore or erase a removed contract document. For the other five
   owners IT admin does (S008; `.claude/CLAUDE.md` § Files). The brief's reason holds (D5: the
   removed list and the restore answer show a quote's title); the consequence is that only the site's
   manager or admin can erase one.
3. **E1** — upload needs `contract:edit` **and** `contract:read_senior`. The roadmap left this to the
   brief (R02.3 *Note*). The brief's answer is sound: a writer who cannot list, open or remove what
   they uploaded would upload blind.

## Findings

### BR1-01 — minor — Q1 and E2 are not marked as taken under the delegation

- **Problem.** § 9 says for Q1 only "recommended a" and for E2 only "Departure stated". S080 and S081
  write "Taken as recommended by the orchestrator under the delegation of 30-10-2026; KLA may
  override at gate B" on each judgement call, so KLA finds them at gate B.
- **Why it matters.** Q1 changes behaviour for every owner; E2 departs from a rule in
  `.claude/CLAUDE.md` § Files. Both must reach KLA, not sit in a section KLA reads as settled.
- **Options.** (a) Add the sentence to Q1 and E2 in § 9, as S080 § 9 does — **recommended**.
  (b) Leave as is and rely on the gate B summary (one more place to forget it).

### BR1-02 — minor — the line for users who may not read the documents

- **Problem.** § 5.7: engineers, IT admin and the floor see one line on the contract page, "The signed
  contract and quotes are kept here by the managers of SMTW." S081 B8 rejected placeholder cards
  because "an empty greyed card raises questions nobody can answer yet". This line is the same thing
  in one sentence: it tells an operator about paper they will never see, and "kept here" points at a
  place that, for them, holds nothing. The price (S081 § 5.4) has no such hint: a non-holder sees no
  field and no note. The sentence is also passive (scope B rule 3).
- **Why it matters.** One main job per screen; nothing on it the user does not need. For the floor
  the line is noise; for the engineer the useful answer is already there (the *Covered* / *Not
  covered* terms, the brief's own "After S083").
- **Options.** (a) Show nothing to a non-holder, as for the price: the cards appear only with
  `can_read_documents` — **recommended** (less to build, less to test; drop the third e2e test's text
  assertion and keep "no *Documents* card, no *Add document*"). (b) Keep a line only for
  `can_edit` holders (the engineers who work with the contract), active voice: "The managers of SMTW
  keep the signed contract and quotes here." (c) Keep it for everyone, reworded as in (b).

### BR1-03 — minor — the device row: no iPhone, and a camera check already done

- **Problem.** § 5.6 says the 1024-byte header rule is *to verify* for Safari, yet § 8.5's row runs on
  an Android phone only. iPhones are in use (rows 46, 52, 56 of `docs/steps/device-checks.md`), and
  the Fuji quote is the one real file this rule exists for. The row's second half (*Add photo* offers
  the camera, the thumbnail shows) is the shared `DocumentsCards` path already proven on a real
  device (rows 5, 46, 51, 56).
- **Why it matters.** A manager with an iPhone opens the quote and sees a blank viewer; nobody
  checked it. The camera half costs IT Admin time for nothing new.
- **Options.** (a) One row: on an **Android phone and an iPhone**, upload the Fuji PDF from Files and
  open it; the pages show. Drop the camera half — **recommended**. (b) Two rows (Android important,
  iPhone plain). (c) Keep as written.

## Nits

- **BR1-04** (nit) § 1 item 5 says "spaces, tabs and line breaks"; § 5.6 strips `b" \t\r\n\f"` (form
  feed too). Name the same set in both, or drop `\f` (the Fuji file needs only `\n`).
- **BR1-05** (nit) § 3 backend: when `_read_upload` passes `data[:HEADER_WINDOW]`, documents.py's
  import of `SIGNATURE_BYTES` becomes unused; say the coder removes it from the import list
  (`SIGNATURE_BYTES` stays in documents_core for the WebP rule).
- **BR1-06** (nit) § 5.1: `read_contract` selects `active`, which no rule of this step reads (E4: no
  state rule). Select `id, site_id` only, as `lock_contract_for_change` does.
- **BR1-07** (nit) § 5.1 last bullet: "a phone photo of a signed page is the floor's way to file
  paper" — the floor cannot upload here (managers only). Write "the manager's way".
- **BR1-08** (nit) § 5.5: build the contract branch with the existing `_scoped_branch`, with
  `search_column` `CONCAT_WS(' ', c.title, c.contract_number)` (NULL-safe) and `unit_column`
  `c.site_id` over the site ids, instead of a hand-built block like the lesson's. One less copy of
  the search and scope SQL.
- **BR1-09** (nit) § 5.4 and § 9: S084 (drafted in parallel) locks contract rows `FOR UPDATE` in its
  daily scan, several per transaction in id order (`alerts.lock_contract_for_scan`, S084 § 5.4). No
  cycle with the documents path (it holds one lock and waits on nothing after it), but "Neither
  holds another lock before it" will be false once S084 lands. Add S084's note to the deadlock check
  and to the staleness list.
- **BR1-10** (nit) § 5.1: the `contracts_bp` route list omits S082's `/for-equipment/<int:node_id>`.
  It still does not end in `/documents`; name it so the staleness check has the full list.

## Checked and found consistent

- **The sixth owner against the five.** `Owner(column, path, log_name, read, read_for_change,
  lock_for_change, lock_for_purge, read_key, write_key, purge_key)` (`backend/documents.py:166`):
  the brief's tuple has the ten fields in order; `lock_for_purge` = `lock_for_change`, as the model's
  and the lesson's (no state rule). The three functions' signatures match the slots and
  procedures.py's pattern (`read_procedure(cur, id, _key=None)`, `…_for_change(cur, id, key)`,
  `lock_…(cur, id, key)`). `_owner_key` checks the key at any site, then the function at the site:
  the engineer (edit, no `read_senior`) → 403 on upload; a manager of another site → 404 (no role at
  the site, so no `read_basic` there); IT admin → 403 on every contract route and no contract rows in
  the removed list. `_REMOVED_CONTRACT_BRANCH` has the 17 UNION columns in the right order;
  `_removed_item` needs its own case before the node `else` (the brief says so); `restoreBlocked`
  returns "" for a contract row (`lifecycle` NULL, no `state`). `file_store._OWNER_FOLDERS` and
  `owner_files("contract", id)` work as described.
- **Permissions and holders.** `equipment:purge_documents` is `("maint_manager", "it_admin")` and in
  `SITE_SCOPED` (`backend/config_rbac.py:99`, `:200`); `has_perm_at` returns True for admin and for a
  token-role key (IT admin's `contract:read_basic`, `contract:edit`), so § 5.2's table holds;
  `require_perm_at` answers "You can't do this at SMTW". `sites_holding` asserts the key is in
  `SITE_SCOPED`: both keys the removed list intersects are.
- **The PDF header rule does not weaken the type check** (self-check 12). (1) Only PDF whitespace
  bytes may precede the header, and NUL is refused, so the first non-whitespace bytes are `%PDF-`; a
  browser's MIME sniff, which skips leading whitespace before looking for `<html`, `<script` and the
  like, cannot see a tag. (2) The file is served with `application/pdf` from the server's own
  detection and `X-Content-Type-Options: nosniff` (`_serve`), so the client never sniffs. (3) The
  check never read past the header for any owner; a PDF with scripts inside passed before and passes
  now, unchanged. (4) The image rules stay at offset 0 (`startswith`), so a whitespace-prefixed image
  is still refused. (5) The window and the test cases agree: `b"\n" * 1019 + b"%PDF-"` is exactly 1024
  bytes and passes; `b"\n" * 1020 + b"%PDF-1.7"` cut at 1024 ends in `%PDF` and is refused. Fact:
  ISO 32000-1 / PDF Reference 1.7 Appendix H note 13 says Acrobat requires only that the header
  appear in the first 1024 bytes; Chrome's PDFium scans the first 1024 bytes for `%PDF`
  (`GetHeaderOffset`). Safari: see BR1-03.
- **The facts.** `scratch/AMC14082369550_12606 (1).pdf` starts with six `\n` then `%PDF-1.7`; the
  other four PDFs in `scratch/` start with `%PDF-` (`od -c`). `detect_file_type` is at
  `backend/documents_core.py:57` and tests `startswith(b"%PDF-")`; `_read_upload` passes
  `data[:SIGNATURE_BYTES]` at `backend/documents.py:306`. `_PRECONDITIONS` holds 20, 25 and 34
  (`backend/local_db.py:1511`). v41 drops and re-adds `chk_equipment_documents_owner` with the three
  statements the brief copies. `TestDetectFileType::test_anything_else_is_none` has no
  whitespace-then-`%PDF-` case; `TestUploadRefusals` refuses `PK\x03\x04…`, `MZ…`, a PDF as a photo and
  a JPEG as a document — none starts with whitespace. `TestOwnerCheckConstraint`'s three tests assert
  the CHECK's name, which v45 keeps. `test_the_unit_scope_is_enforced_fail_closed`'s `nobody` is an
  engineer with no `contract:read_senior`, so the contract branch is left out and
  `owner in ("model", "procedure")` holds. `db_down`, `user_at_sites`, `role_client`, `make_vendor`
  exist in `conftest.py`; `_keys`, `_foreign_keys` (v36), `_owner_check_clause`, `_add_document` (v38)
  are what `test_migration_v41.py` imports. `frontend/e2e/fixtures/test-manual.pdf` exists; the
  Settings search box is "Search removed documents" (`lessons.spec.js:220`).
- **Dependencies on S080–S082.** `_contract_out(row, flags)`, `_fetch_contract`, the four keys in
  `SITE_SCOPED`, `can_edit`, `can_read_cost`, `contracts_bp` at `/api/contracts` with `/` and
  `/<int:contract_id>` (S080); `/<int:contract_id>/equipment[/<int:equipment_id>]`, migration v44,
  `ContractView.vue`, the rewritten `contracts.py` LOCK ORDER bullet (S081);
  `auth_utils.sites_holding(cur, key) -> [{id, code, name, active}]` moved from
  `contracts._sites_holding` (S082 § 5.5, B10). S082 has no migration, so v45 is free; S084 takes v46
  (its § 4.1). `DocumentsCards.vue` props `basePath` and `canEdit` cover the case; `DocumentUploadModal`
  pre-fills the title from the file name except a camera's name.
- **Locks.** The documents path takes (C) first and then only `equipment_documents` rows; S080's and
  S081's writes take (C) first too. No cycle (BR1-09 for S084's wording).
- **Migration v45.** Nullable column after `procedure_id`, key `(contract_id, removed_at)`, FK
  `RESTRICT`, CHECK of six, all `IF NOT EXISTS`, no precondition: the same shape as v38 and v41; the
  rollback reasoning holds (older releases name their columns and join their own owner).
- **Standards.** ISO/IEC 27001:2022 Annex A: A.5.15 *Access control*, A.8.3 *Information access
  restriction*, A.8.10 *Information deletion* — the three numbers are right (the brief's "to verify"
  can go). ISO 9001:2015 § 7.5.3 *Control of documented information*; ISO 55001 § 8.3 *Outsourcing*
  (2014 edition; the same clause number in the 2024 edition as far as I know). Each is explained in
  plain words and tied to a rule of the step.
- **Track and size.** Full track is right (a migration, uploads and file serving, locks). 14 code and
  test files and 5 docs, counted; one concern.
- **Tests.** The manual checks are split into Automated (three e2e tests, untagged, each with its own
  contract) and On a real device (one row with account, network and where). The three e2e flows are
  things a browser judges; the device row is the phone's file picker and PDF viewer (BR1-03 on its
  scope). § 8.3 names the tests that run again and why they stay green; the claims were checked.
- **Scope A.** The brief leads with the point, keeps one term per thing (document, owner, the removed
  list) and labels facts and assumptions. BR1-02 and BR1-07 are the only wording findings.

## Feedback

- waste: three briefs (S080, S081, S082; about 1,500 lines) read in full to confirm six names the
  spawn prompt already listed; a one-line pointer per name to its defining section (e.g.
  "`sites_holding`: S082 § 5.5") would have cut that to three section reads (about 10 minutes).
- idea: the facts file's *Screen text in the tests* lists `"contract"` at seven lines of
  `masters.spec.js` that are S079's vendor tests, because the brief writes the word in quotes as a
  search term; a brief could mark search placeholders differently from control labels, or the tool
  could skip a word that is not Title Case.
