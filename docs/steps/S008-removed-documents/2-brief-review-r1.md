```
Step: S008 — Removed documents: list, restore, delete for good
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 16-10-2026
```

# S008 — Brief review, round 1

**Verdict: one `major` finding is open (BR1-01); no `blocker`.** There are
1 `major`, 4 `minor` and 3 `nit` findings.

Not reviewed, as the orchestrator asked: the three decisions made with the
user (the card on Settings; manager and IT admin; row deleted, no tombstone).

Read for this review: the brief; `docs/Plan.MD` § 3, § 5; the two domain docs;
`SMTW-WebApp-Base.md` § RBAC, § API Response Conventions, § File Upload,
§ Table / List, § Form / Modal; S006's brief and both code reviews; S002 § 6;
S007 and S009 briefs; `equipment.py`, `documents.py`, `file_store.py`,
`config_rbac.py`, `auth_utils.py`, `db_helpers.py`, `settings.py`, `app.py`,
`local_db.py` (v6); `conftest.py`, `test_rbac.py`, `test_documents_api.py`,
`test_settings_api.py`; `SettingsView.vue`, `EquipmentDocuments.vue`,
`EquipmentView.vue`, `PagerBar.vue`, `ActiveToggle.vue`, `useDebounced.js`,
`api.js`, `router/index.js`.

## Findings

### BR1-01 — major — The § 9 list tests cannot pass against the session-scoped test DB

**Problem.** § 9 "List" asserts `total` is 2, that `kind=photo` lists one,
and that `per_page=1&page=2` gives "the older one with `total` 2". The tests
run as the manager or IT admin, who hold `equipment:read_all_units`, so their
removed list is unscoped. `conftest._clean_tables` empties the tables **once
per session**, and `test_documents_api.py` (collected first, alphabetically)
leaves removed rows behind: `TestRemove::test_remove_hides_but_keeps`,
`TestEditTitle::test_removed_document_is_404`, and more as S006/S009 grow.
Within the S008 file itself, each test adds removed rows the next test sees.
So `total == 2` and the paging assertion fail as written, and "newest first"
would be checked against other tests' rows.

**Why it matters.** The coder will hit this on the first run and have to
invent the isolation rule alone, or write assertions that pass only in the
current collection order (flaky; the next step breaks them). The brief's tests
are its acceptance; they have to be runnable as written.

**Options.**
1. **Scope every list assertion through the search box** (recommended). The
   class code from `uniq.class_code()` is unique per test and is the prefix of
   every node code of that class. Make the two nodes of the "List" test with
   one class (`make_equipment(cls=cls)` twice → `ABCD001`, `ABCD002`) and
   query `q=ABCD`: `total` is exactly 2, newest first, both `unit`/`full_path`
   rows, and `per_page=1&page=2&q=ABCD` is the older one. `kind=photo&q=ABCD`
   lists one. The "active one is not listed" check is by id. The fail-closed
   unit-scope test already isolates by unit and needs no change.
2. Assert by id only and never on `total` or page position. Weaker: paging
   and ordering stay untested.
3. A per-test cleanup fixture deleting `equipment_documents` rows. Fights the
   session-scope design of `conftest.py`; rejected.

Add one line to § 9 stating the rule ("every list test filters by `q=<class
code>`, because the test DB is shared across the session and the manager sees
all units").

### BR1-02 — minor — § 5.4 says an unknown `kind` is "ignored, as `_enum_arg`"; `_enum_arg` refuses it with 400

**Problem.** `equipment.py:385-389`: `_enum_arg` raises
`ApiError("kind must be one of: …", 400, "kind")` for any value outside the
allowed set. The brief says "anything else → ignored, as `_enum_arg`", which
is a false claim about the code and leaves the coder with two readings.

**Why it matters.** The list's behaviour on a bad filter should be stated
once and match the equipment list, which 400s.

**Options.**
1. **Reuse `_enum_arg` as it is → 400, field `kind`** (recommended; the card
   only sends `document`/`photo`, so a 400 is never seen in normal use and the
   API stays consistent with `list_equipment`). Reword § 5.4 and add "unknown
   `kind` → 400" to § 9.
2. Ignore it, with a small local check instead of `_enum_arg`. Diverges from
   the equipment list for no gain.

### BR1-03 — minor — After an `OSError`, 204 tells the manager "deleted for good" when the bytes are still on the share; and the thumbnail attempt must not depend on the file's

**Problem.**
- § 5.3 step 4 / § 7: an `OSError` on the file delete → ERROR log, response
  204, "IT removes them by hand from the log's path". A 204 carries no body,
  so the card shows "Deleted 'IMG_2034' for good." The person who acted on a
  privacy request (the § 2 motivating case, DPDP § 12) now believes the
  photo is gone, while the only signal is an ERROR line nobody is reading.
  S006's orphan file (a row never written) is a different class: there the
  user was told the upload failed.
- § 5.3 says `remove_file` "on the file and, when `has_thumb`, on the
  thumbnail". It does not say that a failure on the first still attempts the
  second. A naive `try` around both leaves the thumbnail behind when the main
  file fails (or vice versa).

**Why it matters.** ISO 27001 A.8.10 is met only if someone knows the deletion
did not complete. The record is right (nothing is served), but the user's
understanding is wrong, which is what the standard's "verify deletion" idea
guards against. The second point is a correctness gap the coder would have to
notice alone.

**Options.**
1. **Keep the row-first order and the "never a 5xx after the commit" rule,
   but tell the truth in the response** (recommended): 204 when every file is
   gone; otherwise 200 with `{"files_left": ["<path>"]}` (or a short
   `warning` string). The card's note then reads "Deleted the record of
   'IMG_2034'; the file could not be removed — IT has been told (log)". One
   extra test: the `OSError(EIO)` case asserts the 200 body. Add to § 6 and
   § 8.
2. Keep 204 and accept the gap, but state it plainly in § 7 and in § 10 as an
   assumption the user has signed off ("the manager is not told when the file
   is left behind").
3. 503 after the commit (the brief's rejected alternative): the retry answers
   404 and the user is more confused, not less. Agree with rejecting it.

In either option, state in § 5.3 that each file is attempted on its own: an
error on the file is logged and the thumbnail is still tried, and the log
names each path that failed.

### BR1-04 — minor — The paging and filter helpers are private to `equipment.py`; the brief leaves where they go to the coder

**Problem.** § 5.4: "the coder reuses or lifts those helpers rather than
copying them". `_int_arg`, `_enum_arg`, `_like_pattern`, `DEFAULT_PER_PAGE`,
`MAX_PER_PAGE`, `MAX_PAGE` are all private in `equipment.py:57-61, 374-394`.
S006 § 7 set the rule "no private names imported across modules" (that is why
`load_node_for_user` and `LOCK_EQUIPMENT` were made public). The brief makes
two other names public (`accessible_unit_ids`, `NODE_JOINS`) but does not
settle these five, and "lift" could mean a new module nobody asked for.

**Why it matters.** This is a judgement call the coder would make alone, and
the result is either a cross-module import of `_int_arg` or a copy, both of
which the last two steps ruled out.

**Options.**
1. **Move the three functions and the three constants to `api_common.py`,
   public, with the call sites in `equipment.py` updated** (recommended).
   `api_common.py` already owns request parsing (`clean_body`, `ApiError`);
   query-string parsing belongs beside it. `_like_pattern` has no Flask
   dependency and could go to a core module, but it is only used to build SQL,
   so `api_common` is fine.
2. Make them public in `equipment.py` (`int_arg`, …) and import from there.
   Simpler diff; `equipment.py` then exports general-purpose helpers, which is
   odd for "the tree module".

Say which in § 3 and list `api_common.py` under Backend.

### BR1-05 — minor — Ordering against S009 is unstated, and the inner `JOIN equipment` hides S009's class and type documents

**Problem.** "Depends on" names S006 and says S007 is independent; S009 is
not mentioned, yet both S008 and S009 add routes to `documents.py`, and S009
§ 10.3 explicitly leaves the order to S008's brief ("if S008 is built first,
S009 extends it to the new owners; if after, S008 covers all three owners from
the start"). S008's list joins `equipment_documents` to `equipment` through
`d.equipment_id`; after S009's v7 migration that column is nullable, and an
inner join silently drops every removed class or type document from the card.

**Why it matters.** Whichever lands second must be told what to do; today
neither brief says it, and the coder of the second step would decide alone.

**Options.**
1. **S008 first, as written, and one line in § 10: "S008 is node-only; S009,
   when implemented after it, extends the removed list to class and type
   owners (`LEFT JOIN equipment` plus the owner label), and its brief carries
   that"** (recommended; S008 is the smaller step and S009's brief already
   anticipates this).
2. S009 first; S008 then covers all three owners. Bigger S008; the user said
   the trace and the screen are for a rare action.

Also add S009 to "Depends on" as "independent, but see § 10.5".

### BR1-06 — nit — Card states and width

- **A page past the end after an action.** § 6 says `PagerBar` handles it
  (Prev only). True while `total > 0`; but `PagerBar` is `v-if="total > 0"`,
  so when the last item on page 2 is deleted and `total` becomes 0 the bar
  disappears while `page` stays 2. The next reload (a new removal elsewhere)
  then shows an empty page 2 with "Page 2 of 1". Simplest rule: after a
  restore or purge, if the reloaded page has no items and `page > 1`, load
  `page - 1`. One line in § 6.
- **The empty-page state.** `EquipmentView` has "No equipment on this page."
  for `items.length === 0 && total > 0`; § 6's states list has no equivalent.
  Add "No removed documents on this page."
- **Width.** `SettingsView.vue` caps `.db-card, .settings-card` at 640 px.
  A six-column table with a path needs the full content width; say the new
  card is not given `settings-card` (or has its own class without the cap).
- **Search field.** The card shows `original_name` under the title, and the
  purge note quotes the title; phone photos arrive as `IMG_2034` in both.
  Consider `d.original_name` in the `q` match (three `LIKE`s instead of two);
  otherwise state that the original name is not searched.

### BR1-07 — nit — Standards: small corrections and one addition

The citations are right in substance; three refinements for the owner's
learning:

- **ISO 55001 § 7.6.3.** The clause number is from the **2014** edition
  (7.5 information requirements, 7.6 documented information, 7.6.3 control).
  ISO 55001 was revised in **2024**; cite the edition
  ("ISO 55001:2014 § 7.6.3") so the reference stays checkable. What the clause
  asks for, in plain terms: decide who may read, change, keep and dispose of
  each record, and keep that decision in force for the record's whole life.
  The brief's reading (S006 = retention, S008 = disposition) is a good one.
- **ISO 27001:2022 A.8.10.** The control text says information "shall be
  deleted when no longer required"; "so that it cannot be recovered" is from
  the implementation guidance (ISO 27002 § 8.10), not the control. Worth the
  distinction here because `os.remove` is not secure erasure and the backups
  keep the bytes, which § 2 already admits. Word it as: A.8.10 asks for
  deletion when no longer required and for the deletion to be verified; the
  file is unlinked, the backup copies lapse on IT's schedule.
- **Segregation.** "Segregation of hiding from erasing" is ISO 27001 control
  **A.5.3 (segregation of duties)** rather than A.8.2 (privileged access
  rights). Both apply: A.8.2 is why the key is separate and held by two roles;
  A.5.3 is why remove and erase are two people's actions. Cite both.
- **DPDP Act 2023.** § 12 (the Data Principal's right to erasure) is right;
  the plant's own duty is **§ 8(7)**: a Data Fiduciary erases personal data
  once its purpose is served, unless a law requires keeping it. Mention it;
  it is the clause that makes "delete for good" a duty, not only a request.
- The "not touched" line for TPM / ISO 14224 is correct.

### BR1-08 — nit — Small omissions the coder would otherwise settle

- **`full_path`.** § 5.4 says "built with `equipment_core.full_path` from the
  site, unit and the up-to-three codes the join returns". That is exactly
  `equipment._path(node)` (`equipment.py:130-132`), which is private. Either
  make `_path` public alongside `NODE_JOINS`, or say the three-line build is
  repeated in `documents.py`. Recommend the former.
- **Lock-order notes.** `equipment.py:32-34` says "documents.py (S006) takes
  lock (1) only"; line 204 says "only these helpers, the list and /my-units
  touch _accessible_unit_ids"; S002 § 6 says the same. § 3 updates the
  `documents.py` docstring only. Add: the `equipment.py` docstring line gains
  "(S006, S008)", and the line-204 comment names the removed list as the one
  caller outside the module.
- **Test file helpers.** § 3 leaves the coder to choose between importing
  from `test_documents_api.py` and moving the helpers to `conftest.py`.
  `backend/tests/__init__.py` exists, so the double-import risk of CR1-06
  does not arise; the coupling does. Decide one: move `_upload`, `_uploaded`,
  `_list`, `_folder_files`, `_scrap`, `PDF`, `JPEG` and the `unit`/`node`/
  `at_unit` fixtures to `conftest.py` (what CR1-06 asked for; closes it at
  the same time), or keep the import and say so.
- **`caplog`.** The INFO lines are on logger `documents` (module
  `__name__`); the tests need `caplog.set_level(logging.INFO, logger="documents")`
  as `test_settings_api.py:29` does, or they see nothing. One line in § 9.
- **The `OSError` test target.** "`os.remove` raising `OSError(EIO)`
  (monkeypatched on `file_store`)": `file_store.os` is the global `os`
  module, so that patch hits every `os.remove` in the process for the test's
  duration. Patch `file_store.remove_file` instead (a wrapper that raises for
  the main file and calls through for the thumbnail), as S006's tests patch
  `file_store.write_file`.
- **Missing file at purge.** "A missing file is fine" — agreed for the
  outcome, but a row whose file is already gone is the same "mount or backup
  is wrong" sign that `_serve` logs at ERROR (`documents.py:210`). Log it at
  WARNING with the path, so the pattern is visible.
- **The DELETE.** Step 3 `DELETE … WHERE id = %s`; add `AND equipment_id = %s`
  as the S006 remove does, so the statement can never delete across nodes
  even if a later edit moves the SELECT.
- **§ 3 Docs.** Plan § 3's matrix is a table by role; note that `admin` is
  not listed there (bypass), so the new row shows ✓ for manager and it_admin
  only.

## Checked and found consistent

- **Lock order and races.** Restore and purge both take lock (1) only
  (`_lock_node_for_change` / `load_node_for_user(for_update=True)`) and then
  touch `equipment_documents`, which nothing else locks: no new cycle with
  `equipment.py` or `masters.py`. Restore ↔ restore, restore ↔ purge and
  purge ↔ remove are all serialised on the node row; the second finds the row
  absent or `removed_at` NULL and answers 404/409 as the brief says.
- **Row first, then files.** After the DELETE commits nothing can list, serve
  or restore the document, so a file deleted afterwards is never deleted from
  under a live row, and a leftover file is never served (`_serve` reads the
  row first). The INFO line after step 3 is right; a rolled-back delete logs
  nothing.
- **Restore clears `removed_*` with a raw UPDATE, not `update_row`**, so
  `updated_at`/`updated_by` keep their S006 meaning (last title edit). The
  item read back through `_read_item` (`removed_at IS NULL`) under the lock
  cannot be `None`.
- **Scrapped rule.** Restore refused (409) via `_lock_node_for_change`; purge
  allowed via `load_node_for_user` without the scrapped check. Consistent with
  S002 § 6 ("scrapped = read-only" is about the asset record) and the reason
  in § 7 holds.
- **Unit scope.** `accessible_unit_ids` returns `None` for both roles that
  hold the new key (they hold `equipment:read_all_units`), and the empty-set →
  empty-page rule matches `list_equipment`. The fail-closed test's
  monkeypatch works: `conftest._inject_test_user` recomputes permissions per
  request from the live `PERMISSIONS` dict.
- **`NODE_JOINS` split.** `_NODE_FROM` is `" FROM equipment e"` + the joins,
  so the proposed split is a pure refactor; the removed list's
  `FROM equipment_documents d JOIN equipment e ON e.id = d.equipment_id` +
  `NODE_JOINS` resolves a part's unit through the same COALESCE and keeps
  "one place a node's unit is resolved". Plain reads only, as the fragment's
  comment requires.
- **Routing.** `documents_bp` is mounted at `/api/equipment`;
  `removed-documents` cannot match `/<int:node_id>` on either blueprint, as
  `/my-units` shows. `POST …/restore` and `…/purge` do not collide with the
  S006 routes.
- **RBAC.** `equipment:purge_documents` follows `module:action`; manager and
  IT admin are the Plan § 3 "housekeeping" roles; `admin` bypasses in code;
  `test_rbac.py`'s matrix rows for `maint_manager` and `it_admin` are the only
  ones to change (engineer does not inherit it). `require_perm` on all three
  routes; `actor()` from the token for the log lines.
- **API shape.** `{items, total, page, per_page}` matches the base
  convention; `stored_name` is never sent; 204 for purge; 200 + item for
  restore.
- **Frontend.** `apiGet`/`apiPost` suffice (`apiPost(url)` sends no body and
  returns `null` on 204). `useDebounced`, `PagerBar`, `formatDateTime`,
  `formatBytes` exist with the signatures the card needs. The in-row confirm
  follows `ActiveToggle`/S006 Remove; no browser `confirm()`; the Settings
  route is open to both roles (`settings:read`). Filters in local state are a
  fair call for a card on another page.
- **No migration** is right: no new column, and `removed_at IS NOT NULL` over
  a few thousand rows needs no index.
- **Logging content.** Titles have control characters stripped at upload
  (S006 § 5.4), so the INFO lines cannot be split by a crafted title.
