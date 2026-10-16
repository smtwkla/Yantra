```
Step: S008 — Removed documents: list, restore, delete for good
Doc: brief-review r2
Author: Brief reviewer (Fable)
Date: 16-10-2026
```

# S008 — Brief review, round 2

**Verdict: no `blocker` or `major` finding is open.** There are 3 `minor` and
4 `nit` findings.

Not reviewed, as in round 1: the three decisions made with the user (the card
on Settings; manager and IT admin; row deleted, no tombstone).

Read for this review: the revised brief; `2-brief-review-r1.md`; S006's brief
(§ 5.5, § 5.6, § 8, § 10, the review log) and its code reviews (CR1-06); S009's
brief as revised after its round 1 (§ 3, § 8, § 10.3); S007's brief and review
for overlap; `docs/Plan.MD` § 3 and § 5; `SMTW-WebApp-Base.md` § RBAC, § API
Response Conventions, § Table / List; `equipment.py`, `documents.py`,
`documents_core.py` (`KINDS`), `file_store.py`, `api_common.py`,
`config_rbac.py`, `auth_utils.py`, `app.py` (blueprint prefixes), `local_db.py`
(v6); `conftest.py`, `test_documents_api.py`, `test_equipment_api.py`
(`equipment.MAX_PAGE`), `test_rbac.py`, `test_settings_api.py`;
`SettingsView.vue`, `EquipmentView.vue`, `EquipmentDocuments.vue`,
`PagerBar.vue`, `ActiveToggle.vue`, `useDebounced.js`, `format.js`,
`datetime.js`, `api.js`, `router/index.js`, `stores/navigation.js`.

**State of the tree.** S006 is committed (`76d7282`), so the brief's
"Depends on: S006 committed" is met. The uncommitted working-tree changes are
S007's (FormModal, the dialogs, nginx.conf) and touch none of S008's files.

## Round-1 answers, verified in the text

| Finding | Where it now stands in the brief | Verified |
|---|---|---|
| BR1-01 session-scoped test DB | § 9 "Isolation rule"; the List bullet filters by `q=<class code>` and checks "not listed" by id | Yes; one gap left for the two `q` cases that cannot carry the class code (BR2-02) |
| BR1-02 `_enum_arg` refuses | § 5.4 "anything else → 400, field `kind`"; § 8; § 9 `kind=video` | Yes |
| BR1-03 truthful purge response; thumbnail attempted on its own | § 1.3, § 5.3 steps 5–6, § 6, § 7, § 8, § 9 (`OSError(EIO)` test asserts the 200 body) | Yes; the text of the warning is BR2-01 |
| BR1-04 private paging helpers | § 3 `api_common.py` (`int_arg`, `enum_arg`, `like_pattern`, three constants, public); § 5.4; § 7 | Yes |
| BR1-05 order against S009; inner join | Depends on; § 1 out of scope; § 5.4 "inner join, right while every document has a node"; § 10.5 | Yes |
| BR1-06 card states and width | § 6: `page - 1` rule, "on this page" state, no `settings-card` cap; § 5.4 `original_name` searched | Yes |
| BR1-07 standards | § 2: ISO 55001:2014 edition; A.8.10 control vs ISO 27002 guidance, `os.remove` and backups; A.5.3 with A.8.2; DPDP § 8(7) | Yes |
| BR1-08 small omissions | § 3 `node_path`, docstring and comment, conftest move, `caplog` logger; § 5.3 `DELETE … AND equipment_id`, missing file at WARNING; § 9 patch `file_store.remove_file`; § 3 Docs admin note | Yes; the conftest move has its own points (BR2-03) |

## Findings

### BR2-01 — minor — The purge warning tells the user "IT has been told", but nothing tells IT

**Problem.** § 5.3 step 6 and § 8: the 200 body is
`{"warning": "The record is deleted, but its file could not be removed from storage — IT has been told"}`.
What happens is an ERROR line in the application log (§ 5.3 step 5). No
notification exists (Plan phase 1: no task queue, no Telegram yet), and the
people who hold `equipment:purge_documents` are the manager and the IT admin
themselves. So the text makes a promise the system does not keep, which is the
same class of problem BR1-03 fixed for the 204.

**Why it matters.** The whole point of the 200-with-warning was that the user's
understanding matches the state of the share (ISO 27001 A.8.10 verification).
"IT has been told" makes the manager stop acting on a privacy request that is
not finished.

**Options.**
1. **Say what is true and what to do** (recommended):
   `"The record is deleted, but its file could not be removed from storage. Ask IT to remove it; the path is in the server log."`
   The card shows it in warning style as § 6 already says. One constant in
   `documents.py` (as `STORAGE_UNAVAILABLE` is), used by the route and quoted
   in the test.
2. Keep "IT has been told" and make it true: not possible in this step
   (no notification channel).

### BR2-02 — minor — The two `q` cases that search a title or an original name are not isolated from other tests' rows

**Problem.** § 9 List: "`q=<part of a title>` and `q=<part of the original
name>` each find one". The isolation rule above it covers `q=<class code>`
only. The search is one box, so a title search cannot also carry the class
code. If the test uploads with the helpers' defaults (`title="Pump manual"`,
`filename="manual.pdf"`, `IMG_2034.jpg` in the S006 tests), the manager's
unscoped list also holds the removed "Pump manual" rows that
`TestRemove::test_remove_hides_but_keeps` and
`TestEditTitle::test_removed_document_is_404` leave behind, and "finds one"
fails on the first full run.

**Why it matters.** The same failure BR1-01 was about, for the two cases the
accepted rule does not reach; the coder would discover it and settle the
isolation alone.

**Options.**
1. **Give the two documents a unique token in the title and the original
   name and search for that** (recommended): e.g. title `f"Manual {cls['code']}"`
   and filename `f"{cls['code']}-nameplate.jpg"`, then `q=<the token>`, with
   `total` 1 and the id asserted. One sentence added to the § 9 isolation rule:
   "titles and original names searched for carry the class code too".
2. Assert by id only for those two cases (the item is in `items`), never on
   `total`. Weaker; ordering and `total` are already covered by the class-code
   cases, so acceptable.

### BR2-03 — minor — The test-helper move: a helper named `list`, importing `conftest`, the `engineer` fixture, and the CR1-06 claim

**Problem.** § 3 `backend/tests/conftest.py`: the helpers move there "as plain
functions, renamed without the underscore", and `test_documents_api.py`
"imports them from `tests.conftest`". Four points:

- `_list` renamed without the underscore is `list`, which shadows the builtin
  in `conftest.py` and in every module that imports it. It needs another name
  (`listed`, `list_documents`).
- pytest's own guidance is not to import from `conftest.py`; it is loaded by
  the plugin machinery, and an explicit import works only because
  `backend/tests/__init__.py` makes both spellings resolve to
  `tests.conftest`. S006 CR1-06 offered the alternative: a plain helper module
  (`tests/documents_helpers.py` or similar) for the constants and functions,
  with only the `unit`/`node`/`at_unit` fixtures in `conftest.py`.
- `conftest.py` already has an `engineer` fixture (`role_client("maint_engineer")`,
  no units); `test_documents_api.py:85` overrides it with `at_unit("maint_engineer")`
  (a fresh user holding the node's unit). The brief moves `at_unit` but says
  nothing about `engineer`; moving the override to `conftest.py` would change
  `engineer` for `test_equipment_api.py` and `test_masters_api.py`, which use
  the unit-less one. State that the `engineer` override stays in
  `test_documents_api.py` (and the new file uses `at_unit("maint_engineer")`
  where it needs a unit; for the 403 cases the unit-less conftest `engineer`
  is fine, since `require_perm` answers before any unit check).
- "This also closes S006 CR1-06's coupling point": CR1-06 is about
  `from tests.test_documents_core import jpeg_with_size`
  (`test_documents_api.py:14`), which this move leaves in place. Either move
  `jpeg_with_size` (and its `_image_bytes`) into the same helper module, or
  drop the claim.

**Why it matters.** Each is a decision the coder would otherwise take alone,
and the first is a trap (`list` shadowed in a test module reads as a bug in
review).

**Options.**
1. **A helper module for the plain parts, fixtures in `conftest.py`, the
   `engineer` override left where it is, `jpeg_with_size` moved too**
   (recommended; then the CR1-06 claim is true).
2. Keep everything in `conftest.py` as briefed, with the helper renamed
   (`listed`) and the `engineer` point stated, and reword the CR1-06 line as
   "partly".

### BR2-04 — nit — The list item carries no `status`, so the card cannot show that Restore will be refused on scrapped equipment

§ 5.1 and § 9 (manual check): Restore on a scrapped node → 409 with the
message. The item (§ 8) has `level` but not `status`, so the row looks like
any other until the click fails. `e.status` is already in the join. Add
`status` to the item and let the card mark the row as the equipment list does
(`text-secondary`, "scrapped" in small text under the code) and disable
Restore with a `title` saying why (Base § Form / Modal: never a silent disabled
button). Delete for good stays enabled. The 409 stays as the backend's answer
for a stale page.

### BR2-05 — nit — S009's `/api` re-prefix of `documents_bp` must carry S008's three routes; neither brief says so yet

S009 § 3 moves `documents_bp` to `/api` and spells out `/equipment/…`,
`/masters/equipment-classes/…`, `/masters/equipment-types/…` for the six S006
routes. S008 adds `GET /removed-documents`, `POST /<node_id>/documents/<doc_id>/restore`
and `…/purge` to the same blueprint under the `/api/equipment` prefix. When
S009 is implemented after S008 (§ 10.5), its coder must respell these three
as `/equipment/removed-documents`, `/equipment/<node_id>/documents/<doc_id>/restore`
and `…/purge`, or the card breaks. S009's brief was written before S008's
routes existed and does not list them. One clause in § 10.5 ("S009's prefix
change respells the three S008 routes; the URLs the card calls do not
change"), and the orchestrator should carry the same point to S009's round 2.

### BR2-06 — nit — Standards: one addition for the owner's learning

The § 2 citations are right as revised. One control fits this step more
exactly than A.8.10 and is worth adding beside it: **ISO 27001:2022 A.5.33
(protection of records).** A.8.10 is about information in general; A.5.33 is
the control for *records*, and its guidance (ISO 27002 § 5.33) is where the
ISMS asks for a **retention schedule** and for records to be **disposed of
when no longer required**, with the disposal controlled. In plain terms: decide
how long each kind of record is kept, who may dispose of it, and keep the act
of disposal itself under control. That is the same idea as ISO 55001 § 7.6.3's
"retention and disposition", seen from the security side, and it is the clause
§ 10.2 (no automatic purge yet) and § 10.3 (backups) are really deferring. One
bullet; no change to the design.

### BR2-07 — nit — Small omissions the coder would otherwise settle

- **`equipment.MAX_PAGE` in `test_equipment_api.py:607,617`.** After the move
  this keeps working only if `equipment.py` does `from api_common import MAX_PAGE, …`
  (the imported name stays a module attribute); `import api_common` with
  `api_common.MAX_PAGE` at the call sites would break the two assertions. Say
  the test references change to `api_common.MAX_PAGE`, so the test names the
  constant's real home and § 9 "stays green after the helper moves" holds
  either way.
- **The list SELECT.** `equipment_documents` and `equipment` both have
  `created_at`, `created_by`, `updated_at`, `updated_by`, `id`; the SELECT must
  list `d.` columns explicitly (a `d.*`-style read would be shadowed), and
  alias the node columns as `node_path` expects (`site_code`, `unit_code`,
  `gp_code`, `p_code`, `code`). One line in § 5.4.
- **"Two nodes of one class" and the level-3 case.** § 9 List asserts a
  component's `unit`/`full_path` are the root's; a component (level 3) needs a
  component-unit (level 2) under an equipment (level 1), so the test makes a
  root, a component-unit and a component of the class (the component-unit
  carries no removed document and does not appear). Reword so the coder does
  not wonder whether `make_equipment(parent=root, level="component")` is meant
  to skip a level (it is refused: `check_parent`).
- **The card's page size.** § 6 does not say whether the card sends
  `per_page`; `EquipmentView` sends `PAGE_SIZE = 50` explicitly "the API
  default". Say the card does the same (so `PagerBar` and the request agree
  even if `DEFAULT_PER_PAGE` ever changes).
- **Confirm state on reload.** After a restore or purge, and on a filter
  change, the in-row confirm (`confirmingId`) is cleared, as
  `EquipmentDocuments.vue` does on a node change. One clause in § 6.

## Checked and found consistent

- **Round-1 answers.** All eight are in the brief text, not only in the Review
  log (table above).
- **Purge order and the truthful response.** Row first under lock (1), commit,
  INFO line, then each file on its own with WARNING (missing) / ERROR
  (`OSError`); 204 only when every file is gone, else 200 `{warning}`; never a
  5xx after the commit. `apiPost` returns `null` on 204 and the JSON on 200, so
  the card can tell the two apart without a status code.
- **`remove_file` contract.** Missing → `False` and the caller logs at
  WARNING; any other `OSError` propagates, unlike `remove_quietly`
  (clean-up, logs and swallows). Patching `file_store.remove_file` in the test
  (as S006 patches `write_file`) leaves the global `os` module alone.
- **Restore.** `_lock_node_for_change` (404 access, 409 scrapped), the
  `removed_at IS NOT NULL` SELECT, a raw UPDATE that leaves `updated_*` alone,
  `_read_item` under the lock; a parallel restore or purge is serialised on
  the node row and answers 404/409 as stated.
- **Lock order.** Both routes take lock (1) only and then `equipment_documents`
  rows; no new cycle with `equipment.py` or `masters.py`. The docstring
  updates in § 3 match S009's § 5.3 wording plan ("the last bullet").
- **Unit scope.** `accessible_unit_ids` returns `None` for both roles that hold
  the key (they hold `equipment:read_all_units`); the empty-set → empty-page
  rule matches `list_equipment`; the fail-closed test's monkeypatch works
  because `conftest._inject_test_user` recomputes permissions per request from
  the live `PERMISSIONS` dict.
- **`NODE_JOINS` / `node_path` / `accessible_unit_ids` refactors.** Pure
  renames and one split; the call sites are `_summary`, `_tracked_state`,
  `_can_access`, `list_equipment`, `my_units`, `_read_node`; no test references
  the private names (only `equipment.MAX_PAGE`, BR2-07).
- **`enum_arg` over `KINDS`.** `documents_core.KINDS = ("document", "photo")`
  exists; the 400 carries field `kind`, as the equipment list's `status`.
- **Routing.** `documents_bp` is mounted at `/api/equipment` (`app.py:136`);
  `removed-documents` cannot match `/<int:node_id>`; the three new rules do not
  collide with S006's six.
- **RBAC.** `equipment:purge_documents` follows `module:action`; manager and
  IT admin only; `admin` bypasses in code; `test_rbac.py`'s matrix rows for
  `maint_manager` and `it_admin` are the only ones to change; Settings is
  gated by `settings:read` in `stores/navigation.js`, held by the same two
  roles, so the card is reachable exactly when it is shown.
- **API shape.** `{items, total, page, per_page}` for the list; 200 + item for
  restore; 204 / 200 `{warning}` for purge; `stored_name` never sent; the
  warning is a flat object, within the base conventions.
- **Card.** `useDebounced`, `PagerBar`, `formatDateTime`, `formatBytes`,
  `router-link`, `userPermissions` exist with the signatures the card needs;
  the in-row confirm follows `ActiveToggle` / S006 Remove; no browser
  `confirm()`; `views/settings/RemovedDocuments.vue` mirrors the
  `views/equipment/`, `views/masters/` layout; no `settings-card` cap.
- **S009 ordering.** § 10.5 answers S009 § 10.3 option (a), S009's own
  recommendation; the inner join is right for S008 and S009's brief carries the
  extension (BR2-05 for the prefix detail).
- **No migration; no index** on `removed_at`: a few thousand rows at most.
- **Standards.** ISO 55001:2014 § 7.6.3, ISO 27001:2022 A.8.10 / A.5.34 /
  A.8.2 / A.5.3 / A.8.15 / A.8.3, ISO 27002 § 8.10, DPDP Act 2023 § 12 and
  § 8(7), ISO 9241-110:2020 "use error robustness": all cited correctly and
  explained in plain terms; "TPM / ISO 14224 not touched" is right.
- **Logging content.** Titles are control-character-stripped at upload (S006
  § 5.4), so a crafted title cannot split the INFO lines; `removed_at` in the
  restore line is a datetime, printed as is.
