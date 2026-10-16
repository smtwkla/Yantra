```
Step: S008 — Removed documents: list, restore, delete for good
Doc: brief
Author: Planner (Fable)
Date: 16-10-2026 (revised 16-10-2026 after brief-reviews r1 and r2)
Status: In code review (approved 16-10-2026 by KLA)
```

# S008 — Removed documents: list, restore, delete for good

S006 made **Remove** hide a document or photo and keep its row and file (ISO
55001 controlled information). Nothing can bring a removed file back, and
nothing can ever erase one. This step adds the housekeeping screen S006 queued:
see what was removed, **restore** a mistaken removal, and **delete for good** a
file that must not exist (a photo with a person in it, a document uploaded to
the wrong plant).

**Depends on:** S006 committed (this step adds routes to `documents.py` and a
card to `SettingsView.vue`, both S006 files). S007 is independent. **S009**
(documents on classes and types, briefed in parallel) is independent too, but
the order matters: S008 goes first, node-only, and S009 extends the removed
list to class and type owners (§ 10.5).

Background reading:
- `docs/steps/S006-equipment-documents/1-brief.md` § 2 (A.8.10 note), § 5.5
  (Remove), § 5.6 (writing safely, lock (1) only), § 8 (API);
- `docs/steps/S002-equipment-register/1-brief.md` § 6 (unit access, scrapped =
  read-only);
- `backend/equipment.py` (the lock order in the module docstring,
  `load_node_for_user`, `_accessible_unit_ids`, `_NODE_FROM`);
- `backend/documents.py`, `backend/file_store.py`;
- `frontend/src/views/SettingsView.vue`, `frontend/src/views/EquipmentView.vue`
  (the paged list pattern), `frontend/src/components/PagerBar.vue`;
- `.claude/SMTW-WebApp-Base.md` § RBAC Pattern, § Table / List Pattern.

Decided with the user before this brief (16-10-2026): the screen lives on the
**Settings** page; **delete for good** is for the maintenance manager and IT
admin; deleting for good **deletes the row and the file** (no tombstone row),
with a log line as the trace.

## 1. What will be built

1. **A "Removed documents" card on the Settings page**, for the maintenance
   manager and IT admin. A paged table of every removed document and photo at
   the user's units, newest removal first: when and by whom it was removed,
   title and original file name, the equipment it belongs to (a link to its
   page, with the path), who uploaded it and when, and the size. A search box
   (equipment code, title or original file name) and a kind filter (all /
   documents / photos).
2. **Restore**: the document is back on its equipment page, listed and served
   as before. Refused on scrapped equipment (the S002 read-only rule).
3. **Delete for good**: the row, the file and its thumbnail are deleted. An
   in-page confirmation says it cannot be undone. Allowed on scrapped
   equipment (§ 5.3). Only a *removed* document can be deleted for good: erasing
   is always a second, deliberate step after removal. If the share refuses to
   delete a file, the card says so (§ 5.3): the user is never told "deleted"
   while bytes remain.
4. **One new permission**, `equipment:purge_documents`, for the maintenance
   manager and IT admin: it covers the list, restore and delete for good.
   Engineers remove (S006) but do not restore or erase; they ask the manager.

**Out of scope:**
- a link from an equipment page to its own removed documents (the search box
  on the card takes the equipment code);
- viewing a removed file from the card (§ 7: restore it, look at it on the
  equipment page, remove it again);
- an automatic purge after a retention period (§ 10.2);
- a "deleted for good" history in the database (decided with the user: the log
  line is the trace);
- removing the empty `DATA_DIR/equipment/<node_id>` folder after its last file
  is deleted (harmless; the next upload reuses it);
- removed documents of classes or types: S009 adds those owners after this
  step and extends the list then (§ 10.5); malware scanning (queued).

## 2. Standards and practice

- **ISO 55001:2014 § 7.6.3 (control of documented information;** the clause
  numbers are the 2014 edition's, revised in 2024). The standard asks that
  documented information be controlled through its whole life, and names
  *retention and disposition* among the activities to control. In plain terms:
  decide who may read, change, keep and dispose of each record, and keep that
  decision in force for the record's whole life, rather than letting anyone
  delete anything. S006 covered retention (Remove keeps the row and file).
  This step covers **disposition**: a removed file is erased only by a senior
  role, as a separate step, and the erasure is logged. **Deliberate departure
  (user, 16-10-2026):** after delete for good the database no longer records
  that the file was ever attached; the trace is the application log line
  (§ 5.3). The alternative, a tombstone row, was rejected as more machinery
  than the plant needs for a rare action.
- **ISO 27001:2022.**
  - **A.8.10 (information deletion):** the control asks that information be
    deleted when no longer required; the guidance (ISO 27002 § 8.10) adds that
    the deletion be verified. Delete for good unlinks the row, the file and the
    thumbnail, and the response tells the user when a file could not be
    removed (§ 5.3), so the deletion is verified for them. Two limits, stated
    plainly: `os.remove` is not secure erasure, and the App-FS share has its
    own backup (S006 § 6.4), so a deleted file stays in the backups until
    their retention lapses on IT's schedule, not Yantra's (§ 10.3).
  - **A.5.33 (protection of records):** where A.8.10 is about information in
    general, A.5.33 is the control for *records*, and its guidance (ISO 27002
    § 5.33) asks for a **retention schedule** and for records to be **disposed
    of when no longer required**, with the disposal itself under control. In
    plain terms: decide how long each kind of record is kept, who may dispose
    of it, and keep the act of disposal controlled. It is ISO 55001's
    "retention and disposition" seen from the security side, and it is what
    § 10.2 (no retention schedule yet) and § 10.3 (backups) defer.
  - **A.5.34 (privacy and protection of PII):** the motivating case is a phone
    photo with a person in it. India's **Digital Personal Data Protection Act,
    2023** gives a person the right to have their personal data erased
    (§ 12) and makes it the organisation's duty to erase personal data once
    its purpose is served (§ 8(7)); this step gives the plant a way to do that.
  - **A.8.2 (privileged access rights)** and **A.5.3 (segregation of
    duties):** erasing information is privileged, so it sits behind its own
    permission held by two roles (A.8.2); and hiding (any engineer, S006) and
    erasing (manager, IT admin) are two people's actions, two steps apart
    (A.5.3).
  - **A.8.15 (logging):** restore and delete for good each write one INFO line
    naming the actor, the document and its equipment, and for delete for good
    also who uploaded and who removed it, so the log keeps what the row no
    longer can.
  - **A.8.3 (information access restriction):** the list is scoped to the
    user's units like every equipment read; today both roles holding the key
    see all units, but the scope is enforced anyway (fail-closed, § 5.1).
- **ISO 9241-110:2020 (use error robustness)** and Nielsen's "error
  prevention": a two-step delete (remove, then delete for good from a separate
  screen, confirmed in place) is the recycle-bin pattern every desktop uses. A
  slip is cheap to undo (Restore); an erasure is hard to do by accident.
- **TPM / ISO 14224:** not touched; this step is about the tool's record
  keeping, not maintenance practice.

## 3. Where

### Backend

- **`backend/config_rbac.py`:** `"equipment:purge_documents": ("maint_manager", "it_admin")`,
  after `equipment:edit`, with a comment that it covers listing removed
  documents, restore and delete for good.
- **`backend/api_common.py`:** the query-string helpers move here from
  `equipment.py`, public, beside `clean_body` (request parsing is this
  module's job): `int_arg`, `enum_arg`, `like_pattern`, `DEFAULT_PER_PAGE`,
  `MAX_PER_PAGE`, `MAX_PAGE`. Their behaviour is unchanged; `equipment.py`'s
  call sites are updated. (No private name is imported across modules, the
  S006 rule.)
- **`backend/equipment.py`** (no route changes):
  - `_accessible_unit_ids` becomes public `accessible_unit_ids` (call sites
    renamed), so the removed list can apply the same unit scope as
    `list_equipment`; the comment above it ("only these helpers, the list and
    /my-units touch …") names the removed list as the one caller outside the
    module;
  - the join part of `_NODE_FROM` becomes a public `NODE_JOINS` and
    `_NODE_FROM = " FROM equipment e" + NODE_JOINS`, so the removed list joins
    `equipment_documents` to a node's root unit through the one fragment that
    resolves a node's unit (the fragment's own comment asks for this);
  - `_path(node)` becomes public `node_path(node)`, so the removed list builds
    `full_path` the same way as the equipment list;
  - the module docstring's lock note reads "documents.py (S006, S008) takes
    lock (1) only …".
- **`backend/documents.py`:** the three routes of § 8 (`GET /removed-documents`,
  `POST …/restore`, `POST …/purge`). The module docstring gains one line: a
  removed document can be restored or deleted for good by
  `equipment:purge_documents` (S008).
- **`backend/file_store.py`:** `remove_file(path)`: removes one file; a missing
  file is not an error (returns False; the caller logs it); any other
  `OSError` propagates (unlike `remove_quietly`, which is for clean-up after
  another error). Used by purge (§ 5.3).
- **`backend/tests/documents_helpers.py`** (new, a plain module, not a test
  file): the document test helpers move here from `test_documents_api.py` so
  both API test files share them without one importing the other, and pytest's
  advice against importing from `conftest.py` is followed: `PDF`, `JPEG`,
  `jpeg()`, `docs_url`, `upload`, `uploaded`, `listed` (was `_list`; `list`
  would shadow the builtin), `refusal`, `folder_files`, `scrap`, and
  `jpeg_with_size` with its `_image_bytes` from `test_documents_core.py`
  (so `test_documents_api.py` no longer imports a test module: this closes
  S006 CR1-06).
- **`backend/tests/conftest.py`:** the `unit`, `node` and `at_unit` fixtures
  move here from `test_documents_api.py`. The `engineer` override
  (`at_unit("maint_engineer")`, a user holding the node's unit) **stays in
  `test_documents_api.py`**: conftest's `engineer` has no units and
  `test_equipment_api.py` / `test_masters_api.py` rely on that.
- **`backend/tests/test_removed_documents_api.py`** (new): § 9. It uses
  `at_unit("maint_engineer")` where a unit matters; for the 403 cases the
  unit-less conftest `engineer` is fine (`require_perm` answers first).
- **`backend/tests/test_equipment_api.py`:** its two reads of
  `equipment.MAX_PAGE` become `api_common.MAX_PAGE`, the constant's new home.
- **`backend/tests/test_rbac.py`:** the new key in the per-role matrix
  (`maint_manager`, `it_admin`).

### Frontend

- **`frontend/src/views/settings/RemovedDocuments.vue`** (new): the card (§ 6).
- **`frontend/src/views/SettingsView.vue`:** renders it below the Uploads card
  when `userPermissions` includes `equipment:purge_documents`.
- `api.js`: nothing new (`apiGet`, `apiPost`).

### Docs

None for the coder. At approval: Plan § 3 (a matrix row for the key: ✓ for
manager and it_admin only; `admin` is not a column there, it bypasses in
code) and Plan § 5 (the `equipment_documents` row: "…or restored; deleted for
good by the manager or IT admin (S008)").

## 4. Data model

**No migration.** Delete for good is a row delete; restore clears
`removed_at`/`removed_by`. No new column or index: the removed list orders by
`removed_at` over a table of at most a few thousand rows, and an index for it
would be premature (CLAUDE-COMMON "right-sized").

## 5. Rules

### 5.1 Who and where

| Action | Permission | Also |
|---|---|---|
| List removed documents | `equipment:purge_documents` | scoped to the user's units through `accessible_unit_ids` (fail-closed: a role holding the key without `equipment:read_all_units` sees only its units) |
| Restore | `equipment:purge_documents` | the node at the user's units (404); not scrapped (409) |
| Delete for good | `equipment:purge_documents` | the node at the user's units (404); **scrapped allowed** (§ 5.3) |

The Settings page itself stays behind `settings:read`; the two role sets are
the same today (manager, IT admin). `admin` bypasses in code, as always.

### 5.2 Restore

In one transaction:
1. `_lock_node_for_change` (lock (1), access → 404, scrapped → 409), as
   title edit and remove do.
2. `SELECT id, title, kind, removed_by, removed_at FROM equipment_documents WHERE id = %s AND equipment_id = %s AND removed_at IS NOT NULL`
   → 404 when none (an active document, another node's, or one already
   restored by a parallel request: the node lock serialises them).
3. `UPDATE equipment_documents SET removed_at = NULL, removed_by = NULL WHERE id = %s`.
4. Read the item (`_read_item`) under the lock and return it (200, the item as
   in the node's list).
5. After the commit, INFO: `Document <id> '<title>' (<kind>) of node <node_id> restored by <actor>; removed by <removed_by> at <removed_at>`.

`updated_at`/`updated_by` are untouched: they record the last title edit
(S006 § 5.8), not a restore. The file was never moved, so nothing happens on
disk. A restored document whose file is missing on disk opens as 404 "File
missing" (S006 § 6.2), logged at ERROR, like any other.

### 5.3 Delete for good (purge)

**Row first, then the files**, so a restore can never race with the erasure
(§ 7):
1. One transaction: `load_node_for_user(for_update=True)` (lock (1), access →
   404). **No scrapped check:** erasing a file is disposition of information,
   not a change to the asset record; a privacy request must not wait for
   equipment that will never be un-scrapped.
2. `SELECT id, title, kind, stored_name, has_thumb, created_by, removed_by, removed_at FROM equipment_documents WHERE id = %s AND equipment_id = %s`
   → 404 when none; **409 "Remove the document first"** when `removed_at` is
   NULL (an active document, or one restored by a parallel request).
3. `DELETE FROM equipment_documents WHERE id = %s AND equipment_id = %s`;
   commit. From here nothing serves or lists the document and nothing can
   restore it.
4. INFO: `Document <id> '<title>' (<kind>, <stored_name>) of node <node_id> deleted for good by <actor>; uploaded by <created_by>, removed by <removed_by> at <removed_at>`.
   Written right after the commit, so the line is never logged for a
   rolled-back delete, and before the file I/O, so it is there even if that
   hangs.
5. Outside the transaction: `file_store.remove_file` on the file and, when
   `has_thumb`, on the thumbnail, **each attempted on its own**: a failure on
   the first never skips the second. For each file:
   - already missing → WARNING with the path (the same "mount or backup is
     wrong" sign `_serve` logs; the outcome is fine);
   - any other `OSError` → ERROR with the path, errno and message; the file is
     counted as left behind.
6. **The response tells the truth.** Every file gone (or already missing) →
   **204**. Any file left behind → **200** with `{"warning": FILE_LEFT_BEHIND}`,
   one constant in `documents.py` (as `STORAGE_UNAVAILABLE` is), quoted by the
   test:
   `"The record is deleted, but its file could not be removed from storage. Ask IT to remove it; the path is in the server log."`
   It says what is true and what to do; nothing notifies anyone (no queue or
   Telegram yet), and the people clicking are the manager and IT admin
   themselves. The thumbnail alone left → the same text; the paths are in the
   log, never in the response, as `stored_name` is never sent. The record is
   gone and the leftover bytes are never served. A 503 after the commit was
   rejected: a retry would find nothing to delete and answer 404.

The empty node folder is left as it is.

### 5.4 The removed list

- Items: the removed documents at the user's units, `ORDER BY removed_at DESC, id DESC`.
- Paged: `page` (default 1, at most `MAX_PAGE`) and `per_page` (default
  `DEFAULT_PER_PAGE` = 50, at most `MAX_PER_PAGE` = 200), through
  `api_common.int_arg`, exactly as `list_equipment`.
- Filters: `kind` through `api_common.enum_arg` over `KINDS` (`document` |
  `photo`; anything else → **400, field `kind`**, as the equipment list
  refuses a bad `status`); `q` (trimmed; matches `e.code`, `d.title` or
  `d.original_name` with `LIKE %q%`, `like_pattern` escaping; the original
  name too because phone photos are `IMG_2034` in both title and name).
- Unit scope: `accessible_unit_ids`; an empty set → the empty page, as
  `list_equipment`.
- Each item (§ 8) carries the node's `equipment_id`, `code`, `name`, `level`,
  `status`, `unit` (`SITE.UNIT`) and `full_path` (`equipment.node_path` over
  the join's site, unit and up-to-three codes), so the row links to the
  equipment page, reads like the equipment list, and the card can mark a
  scrapped node (§ 6).
- The join is `FROM equipment_documents d JOIN equipment e ON e.id = d.equipment_id`
  + `NODE_JOINS`: an inner join, right while every document has a node (S009
  changes that; § 10.5). Both tables have `id`, `created_at`, `created_by`,
  `updated_at`, `updated_by`, so the SELECT names every `d.` column
  explicitly (never `d.*`) and aliases the node columns as `node_path`
  expects (`site_code`, `unit_code`, `gp_code`, `p_code`, `code`).

## 6. The card

On the Settings page, below Uploads, when the user holds
`equipment:purge_documents`:

- **Header:** "Removed documents", with the total when loaded.
- **Filters:** a search box ("Search equipment code, title or file name…",
  debounced with `useDebounced`, as the equipment list) and a kind select
  (All / Documents / Photos). A filter change goes back to page 1. Filters are
  local state, not URL query: this is a card on the Settings page, not a page
  of its own.
- **Width:** the card takes the full content width (it does **not** get the
  `settings-card` class, which caps the other cards at 640 px); a six-column
  table with a path needs it.
- **Table** (`table-sm`, `table-responsive`), one row per item:
  - Removed: `formatDateTime(removed_at)` and `removed_by`;
  - Title: a kind icon (PDF / image), the title, the original name underneath
    in small text;
  - Equipment: a `router-link` to `/equipment/<equipment_id>` showing the code
    and name, the `full_path` underneath in small text; a scrapped node's row
    is `text-secondary` with "scrapped" in small text under the code, as the
    equipment list marks them;
  - Uploaded: `created_by`, `formatDateTime(created_at)`;
  - Size: `formatBytes(size_bytes)`;
  - Actions (last column, right-aligned): **Restore** (`btn-outline-primary`)
    and **Delete for good** (`btn-outline-danger`, bin icon). On a scrapped
    node Restore is disabled with `title="Scrapped equipment cannot be
    changed"` (never a silent disabled button); Delete for good stays enabled.
    The backend's 409 remains the answer for a stale page.
- **Page size:** the card sends `per_page=50` explicitly (a `PAGE_SIZE`
  constant, as `EquipmentView` does), so `PagerBar` and the request agree
  even if the API default ever changes.
- **Delete for good** turns the row's action cell into an in-page confirm, the
  house pattern (`ActiveToggle`, S006 Remove): "Delete for good? The file cannot
  be recovered." **[Delete for good]** (`btn-danger`) **[No]**. No browser
  `confirm()`.
- **After an action:** the list reloads; a one-line note above the table says
  what happened ("Restored 'Pump manual'." / "Deleted 'IMG_2034' for good."),
  since one of the two cannot be undone. A purge answered with a `warning`
  (§ 5.3) shows that warning text instead, in warning style, so the user
  knows the file is not gone. An error shows in an alert above the table.
  Buttons are disabled while an action is in flight. The in-row confirm is
  cleared on every reload and filter change, as `EquipmentDocuments` clears
  it on a node change. **Page after an action:** if the reloaded page has no
  items and `page > 1`, the card loads `page - 1` (so deleting the last item
  of page 2 never strands the user on an empty page 2, which `PagerBar` hides
  when `total` is 0).
- **States:** "Loading…", a load error with Retry, "No removed documents." or,
  with a filter, "No removed documents match.", and "No removed documents on
  this page." when `total > 0` and the page is empty (an old page number, as
  the equipment list).
- **Not shown:** thumbnails, Open or Download. A removed file is not served
  (S006 § 5.5); to look at one, restore it, open it on the equipment page and
  remove it again (§ 7).

## 7. Design decisions

| Decision | Reason | Rejected alternative |
|---|---|---|
| The screen is a card on Settings (user, 16-10-2026) | Housekeeping by the two senior roles, who already live on Settings | A section of the Equipment module; a per-equipment "show removed" switch |
| One key `equipment:purge_documents` for list, restore and purge (manager, IT admin) | The screen is one job for one group; a separate restore key would grant the same two roles today | `equipment:edit` for restore (engineers would hold a right the UI does not offer them; S006 CR-style gap); two keys |
| Delete for good deletes the row (user, 16-10-2026) | Simplest; the INFO line is the trace | A tombstone row (`purged_at`/`purged_by`) kept forever |
| Erasure only of a *removed* document; 409 otherwise | Two deliberate steps, by two levels of people, before bytes are gone (recycle-bin pattern) | Delete for good straight from the equipment page |
| Row first, then the files | After the commit nothing can restore the document, so the file is never deleted from under a live row; a leftover file on an I/O error is never served | Files first (a restore between the file delete and the row delete leaves a live row with no file) |
| An `OSError` while deleting a file → 200 with a `warning`, plus an ERROR log | The record is gone and nothing serves it, but the user must not be told "deleted" while bytes remain (A.8.10 verification; the privacy case); the leftover is an IT task with the path in the log | 204 regardless (the card would say "deleted for good" falsely); 503 after the commit (the retry would find nothing to delete and answer 404) |
| Query-string helpers moved to `api_common.py`, public | Both lists parse the same arguments; no private name crosses a module (S006 rule); request parsing already lives there | Public names left in `equipment.py` (the tree module exporting general helpers); a copy in `documents.py` |
| Purge allowed on scrapped equipment; restore refused | Erasure does not change the asset record; restoring does | Both refused (a privacy request blocked by a scrapped flag) |
| No file access from the card | Keeps S006's "removed = never served" rule and its blob code untouched; restore-look-remove covers the rare case | Serving removed files to key holders; thumbnails on the card |
| No migration, no index on `removed_at` | A few thousand rows at most; the scan is nothing | `ix_equipment_documents_removed` |
| Restore clears `removed_by`, logs the old value | The item then reads as any active document; the trace is in the log | Keeping `removed_by` on an active row; `restored_at`/`restored_by` columns |
| Filters in local state, not the URL | A card on the Settings page; a bookmarkable filter has no use here | The equipment list's URL-query pattern |

## 8. API

On `documents_bp` (mounted at `/api/equipment`; `removed-documents` is not an
integer, so it never clashes with `/<int:node_id>/documents`, as `/my-units`
does not):

| Method and path | Permission | Result |
|---|---|---|
| `GET /removed-documents?page&per_page&kind&q` | `equipment:purge_documents` | `{items, total, page, per_page}`; items: `id, kind, title, original_name, content_type, size_bytes, created_at, created_by, removed_at, removed_by, equipment_id, code, name, level, status, unit, full_path`; 400 field `kind` / `page` / `per_page` for a bad value |
| `POST /<node_id>/documents/<doc_id>/restore` | `equipment:purge_documents` | 200, the item as in the node's list (§ 5.2); 404 not removed / other node / no access; 409 scrapped |
| `POST /<node_id>/documents/<doc_id>/purge` | `equipment:purge_documents` | 204 when every file is gone; 200 `{warning: FILE_LEFT_BEHIND}` when a file was left on the share (§ 5.3); 404 unknown / other node / no access; 409 "Remove the document first" |

`stored_name` is never sent (S006).

## 9. Tests and acceptance

### API (`test_removed_documents_api.py`)

**Isolation rule:** the test DB is emptied once per session and the manager
sees all units, so other tests' removed rows are in the list too. Every
assertion on `total`, order or page position therefore **filters by
`q=<class code>`**: the test makes its nodes with one class from
`uniq.class_code()`, whose code is the prefix of every node code of that
class (`ABCD001`, `ABCD002`), and checks "not listed" by id. The titles and
original names a test searches for carry the class code too (title
`f"Manual {code}"`, file name `f"{code}-nameplate.jpg"`), never the helpers'
defaults ("Pump manual", `IMG_2034.jpg`), which other tests leave behind as
removed rows.

- **List:** three nodes of one class, a root, a component-unit under it and a
  component under that (a component needs both levels above it); upload a PDF
  on the root and a photo on the component, remove both, and a third document
  on the root that stays active → with `q=<class>` the two removed are listed
  newest removal first with `code`, `name`, `level`, `status`, `unit`,
  `full_path`, `removed_by`, `total` 2; the active one's id is not there; the
  component's `unit` and `full_path` are the root's. `kind=photo&q=<class>`
  lists one; `q=<the token in the title>` and `q=<the token in the original
  name>` each give `total` 1 with the expected id; `per_page=1&page=2&q=<class>`
  gives the older one with `total` 2; `kind=video` → 400 field `kind`.
- **List access:** engineer and operator → 403; manager
  (`role_client("maint_manager")`) and IT admin → 200. **Unit scope,
  fail-closed:** with `config_rbac.PERMISSIONS["equipment:purge_documents"]`
  monkeypatched to include `maint_engineer`, an engineer holding unit A does
  not see unit B's removed documents, and one holding no unit gets an empty
  page.
- **Restore:** 200 with the item; back in the node's list; `/file` serves
  again; `removed_at` and `removed_by` NULL in the row; `updated_by`
  unchanged; an INFO line with the actor and the remover; a second restore →
  404; an active document → 404; another node's `doc_id` → 404; a scrapped
  node → 409; engineer → 403.
- **Purge:** 204; the row is gone; the file and the thumbnail are gone from
  the node folder, the other files stay; the node's list is unchanged; a
  second purge → 404; `/file` → 404; restore after purge → 404; an active
  document → 409 "Remove the document first"; another node's `doc_id` → 404;
  a scrapped node → 204; engineer → 403; the file already missing on disk →
  204 and a WARNING line naming the path; `file_store.remove_file`
  monkeypatched to raise `OSError(EIO)` for the main file and call through
  for the thumbnail → **200 with `warning` equal to `FILE_LEFT_BEHIND`**, the
  row gone, the thumbnail gone, an ERROR line naming the main file's path; an
  INFO line naming the actor, the uploader and the remover.
- **Logs:** the INFO and WARNING lines are on logger `documents`, so the tests
  use `caplog.set_level(logging.INFO, logger="documents")` as
  `test_settings_api.py` does.
- **RBAC matrix** (`test_rbac.py`): the key is in the manager's and IT admin's
  permission sets and nobody else's.
- **Unchanged behaviour:** `test_equipment_api.py`, `test_documents_api.py`
  and `test_documents_core.py` stay green after the helper moves
  (`api_common`, `documents_helpers`, `conftest`).

### Frontend
- No pure helper is added, so no vitest file. `npx vite build` clean.

### Manual checks (user)
- As an engineer: remove a PDF and a photo on `RPP001`; Settings shows no
  Removed documents card.
- As the manager: Settings → Removed documents lists both, newest first, with
  the link to `RPP001`; search `RPP` finds them; kind Photos shows one.
- Restore the PDF: the note says so; it is back on `RPP001`, Open works.
- Delete the photo for good: the confirm appears; No keeps it; Delete for
  good removes it from the list with the note; the dev `data/equipment/<id>/`
  folder no longer has its file or thumbnail; the backend log has the INFO
  line.
- Scrap a node with a removed document: its row is greyed with "scrapped",
  Restore is disabled with the reason in its tooltip; Delete for good works.
- On a phone: the table scrolls sideways; the confirm buttons are reachable.

### Acceptance
- `tooling/run-tests.bat` green; `npx vite build` clean.
- The manager can bring back a document removed by mistake, and erase a
  photo that must not exist, from one screen.

## 10. Open questions and assumptions

1. **Decided (user, 16-10-2026):** the card lives on Settings; delete for good
   is for the manager and IT admin; the row is deleted, not tombstoned.
2. **Assumption — no automatic purge.** Removed documents stay until someone
   deletes them for good. A retention rule ("delete for good after N days") is
   a later setting plus a worker task; the worker is not built (Plan phase 1).
3. **Assumption — backups.** Delete for good does not reach the App-FS
   backups; their retention is IT's policy. Worth one line in the plant's
   privacy procedure when there is one.
4. **Assumption — engineers do not restore.** They ask the manager; the
   removal note on the equipment page is not changed.
5. **Order against S009 (answers S009 § 10.3, option a):** S008 is built
   first, node-only. S009, implemented after it, extends the removed list to
   class and type owners (a `LEFT JOIN equipment`, or a `UNION` branch, plus
   the owner label and "every unit" access for ownerless documents) and its
   brief carries that extension; nothing in S008 anticipates it. S009 also
   re-prefixes `documents_bp` to `/api`; its coder respells S008's three
   routes (`/equipment/removed-documents`,
   `/equipment/<node_id>/documents/<doc_id>/restore` and `…/purge`) so the
   URLs the card calls do not change. S009's brief, in review in parallel,
   gets this point at its next round.

## 11. Amendments

(none)

## Review log

### Round 1 — `2-brief-review-r1.md` (Fable), answered 16-10-2026

| Finding | Severity | Response |
|---|---|---|
| BR1-01 The list tests cannot pass against the session-scoped test DB | major | **Accepted, option 1.** Every `total`/order/page assertion filters by `q=<class code>`; the isolation rule is stated in § 9. |
| BR1-02 `_enum_arg` refuses, not ignores | minor | **Accepted, option 1.** Unknown `kind` → 400 field `kind` (§ 5.4, § 8, § 9). |
| BR1-03 204 says "deleted" while bytes remain; thumbnail attempt | minor | **Accepted, option 1, adapted.** 204 only when every file is gone; otherwise 200 with a `warning` text, shown by the card in warning style. Paths stay in the log, not the response (`stored_name` is never sent). Each file attempted on its own; a missing file logged at WARNING (§ 1, § 5.3, § 6, § 7, § 8, § 9). |
| BR1-04 Private paging helpers | minor | **Accepted, option 1.** `int_arg`, `enum_arg`, `like_pattern` and the three constants move to `api_common.py`, public; call sites updated (§ 3, § 5.4, § 7). |
| BR1-05 Order against S009; inner join | minor | **Accepted, option 1.** S008 first, node-only; S009 extends the list (Depends on, § 1, § 5.4, § 10.5). |
| BR1-06 Card states and width | nit | **Accepted.** `page - 1` after an action empties the page; "on this page" state; no `settings-card` cap; `original_name` searched (§ 1, § 5.4, § 6). |
| BR1-07 Standards corrections | nit | **Accepted.** ISO 55001:2014 edition; A.8.10 control vs guidance, `os.remove` and backups stated; A.5.3 with A.8.2; DPDP § 8(7) (§ 2). |
| BR1-08 Small omissions | nit | **Accepted.** `node_path` public; `equipment.py` docstring and comment; test helpers moved to `conftest.py` (revised in r2: a helper module, BR2-03); `caplog` logger; patch `file_store.remove_file`; missing file at WARNING; `DELETE … AND equipment_id`; Plan § 3 admin note (§ 3, § 5.3, § 9). |

### Round 2 — `2-brief-review-r2.md` (Fable), answered 16-10-2026

All eight round-1 answers verified in the text. No blocker or major finding;
the loop ends here. The answers below are not re-reviewed.

| Finding | Severity | Response |
|---|---|---|
| BR2-01 "IT has been told" is not true | minor | **Accepted, option 1.** The text says what is true and what to do; one constant `FILE_LEFT_BEHIND` (§ 5.3, § 8, § 9). |
| BR2-02 Title and name searches not isolated | minor | **Accepted, option 1.** The searched title and file name carry the class code; `total` 1 with the id (§ 9). |
| BR2-03 The helper move: `list`, importing conftest, `engineer`, CR1-06 claim | minor | **Accepted, option 1.** `tests/documents_helpers.py` for the plain parts (`listed`, `jpeg_with_size` and `_image_bytes` included, so CR1-06 is closed); fixtures in `conftest.py`; the `engineer` override stays in `test_documents_api.py` (§ 3). |
| BR2-04 No `status` in the item | nit | **Accepted.** `status` in the item; scrapped rows greyed, Restore disabled with its reason (§ 5.4, § 6, § 8, § 9). |
| BR2-05 S009's `/api` re-prefix must carry the three routes | nit | **Accepted.** § 10.5; the point is passed to S009's review by the user (S009 is run from another terminal). |
| BR2-06 ISO 27001 A.5.33 | nit | **Accepted.** A bullet beside A.8.10 (§ 2). |
| BR2-07 Small omissions | nit | **Accepted.** `api_common.MAX_PAGE` in the equipment tests; explicit `d.` columns and node aliases; three nodes for the level-3 case; `per_page=50` explicit; the confirm cleared on reload (§ 3, § 5.4, § 6, § 9). |

### Gate A — 16-10-2026

- Approved by KLA as it stands after round 2; no changes asked.
- The S009 route re-spelling point (§ 10.5) is passed to S009's review by
  the user.
