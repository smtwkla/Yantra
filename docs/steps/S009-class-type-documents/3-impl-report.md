Step: S009 — Documents on classes and types
Doc: impl-report
Author: Coder (Opus)
Date: 16-10-2026
Status: n/a (the brief carries the status)

# S009 — Implementation report

## 1. What was built

- **Documents and photos on an equipment class and on an equipment type**, with every S006 rule: PDF documents, JPEG/PNG/WebP photos with thumbnails, the same size limit, title edit, remove hides and keeps. Read with `equipment:read` at every unit; changed with `equipment:edit`. An inactive class or type keeps listing, serving and accepting changes.
- **Masters → Equipment classes / Equipment types**: every row has a **Documents** (paperclip) button, for every user. It swaps the table for that class's or type's Documents and Photos cards inside the same panel, under "← Equipment classes · RPP — Radial piston pump · Documents" (or "← Equipment types · RPP — Closed execution · Documents"). While the cards show, the card header's own controls (Show inactive, the class filter, Add) are hidden. **Back** brings the table back with its filter and switch as they were. Upload, edit title and remove are there for `equipment:edit` only. The upload dialog says "Visible at every unit". The remove confirmation, in the list and in the photo viewer, adds "It disappears from every machine of this class/type."
- **Equipment page**: the Documents and Photos cards also list the node's **type** documents ("From type *Closed execution*") and then its **class** documents ("From class *RPP — Radial piston pump*"), after the node's own. They are read-only there: Open, Download and the viewer, but no Edit or Remove. For editors, each group's heading carries a plain-text "Managed in Masters → Equipment types / Equipment classes". The photo viewer steps through the own and the inherited photos and offers Edit/Remove on the own ones only. "No documents yet." / "No photos yet." appear only when there is nothing at all to show, own or inherited.
- **Migration v7**: `equipment_documents.equipment_id` becomes nullable. The table gets `class_id` and `type_id`, each with an index and an FK, plus `chk_equipment_documents_owner` (exactly one owner). Existing rows and files stay where they are.

## 2. How it works

**Backend (`documents.py`).**
- At the top, an `OWNERS` table maps `equipment` / `class` / `type` to an `Owner`:
  - the owner column (`equipment_id` / `class_id` / `type_id`);
  - the collection URL template (sent back as each inherited group's `path`);
  - three functions:
    - `read`: a plain read, 404 when the owner is missing or not visible;
    - `read_for_change`: the upload's early refusals before any file is touched;
    - `lock_for_change`: the single `FOR UPDATE` in the write transaction.
- How each owner fills those functions:
  - **node**: `load_node_for_user` (unit access), the early scrapped 409, and `_lock_node_for_change` (lock (1), with scrapped and access re-checked from the locked row), all as in S006;
  - **class**: `SELECT id, code, name, active FROM equipment_classes WHERE id = %s`, plain or `FOR UPDATE`;
  - **type**: the same on `equipment_types`, with a plain join for the class code and name. The lock is on the type row alone.
- The six S006 operations (list, upload, file, thumb, edit title, remove) are written once and take `(owner, owner_id)`. Each has three stacked `@documents_bp.route(…, defaults={"owner": …})` decorators, for `/equipment/<owner_id>/documents…`, `/masters/equipment-classes/<owner_id>/documents…` and `/masters/equipment-types/<owner_id>/documents…`, above its `@require_perm`. The blueprint is now registered at `/api`, so the node URLs are unchanged. Every query that used `equipment_id = %s` now uses the owner's column (from the constant table, never from the client). File paths come from `file_store` with the owner.
- **The node list** adds `inherited`:
  - the type group first (when the node has a type), then the class group, each `{owner, id, label, path, items}`, newest first, removed documents left out;
  - a group with no documents is dropped;
  - the type label is the `type_name` that `load_node_for_user` already returns; the class label ("RPP — Radial piston pump") comes from `documents.py`'s own `_read_class`, so `equipment._NODE_COLUMNS` is not widened;
  - class and type lists have no `inherited` key.
- **Locks**: a write takes exactly one owner lock — node (1), class (4) or type (5) — and then touches only `equipment_documents`. The `documents.py` docstring and the last bullet of `equipment.py`'s lock-order docstring say so.
- **S008's routes** (removed list, restore, delete for good) stay node-only. They are re-prefixed with `/equipment/`, so their URLs are unchanged, and their `_read_item` / `file_store.file_path` calls pass `"equipment"`. `_lock_node_for_change` kept its name, so S008's calls to it are untouched.

**Storage (`file_store.py`).** `owner_folder(owner, owner_id)` maps `equipment` / `class` / `type` to `equipment/`, `equipment-classes/`, `equipment-types/` under `DATA_DIR`. It replaces `node_folder`. `file_path` and `write_file` take `(owner, owner_id, …)`.

**Frontend.**
- `components/documents/DocumentsCards.vue` (moved from `views/equipment/EquipmentDocuments.vue`) takes `basePath`, `canEdit` and `everyUnit`.
- On load it tags every item with the `path` it is served from (`basePath` for its own, the group's `path` for inherited ones) and with `own`. File and thumbnail URLs are `${item.path}/${id}/file|thumb`, and the edit and remove buttons show only on `own` items. Document ids are unique across owners, so the object-URL caches stay keyed by id.
- The watcher follows `basePath`, which covers both a new node and a new class or type in Masters.
- The upload and title dialogs take `basePath` instead of building the node URL. `PhotoViewer` gets every photo shown, plus `removeNote`, and offers Edit/Remove only when `canEdit && photo.own`.
- The Masters panels hold a `documentsFor` ref and render `DocumentsCards` in place of the table while it is set.

## 3. Files touched

| File | Change |
|---|---|
| `backend/local_db.py` | Migration v7 (§ 4 of the brief, statement for statement). |
| `backend/file_store.py` | `owner_folder(owner, id)` replaces `node_folder`; `file_path` / `write_file` take the owner; docstring layout. |
| `backend/documents.py` | Owner table and loaders/lockers; the six operations generalised with three stacked routes each; `inherited` on the node list; docstring (owners, A.8.3, lock note); S008 routes re-prefixed `/equipment/…` and their helper calls updated. |
| `backend/app.py` | `documents_bp` registered at `/api`. |
| `backend/equipment.py` | Docstring only: the `documents.py` lock bullet (one owner lock: (1), (4) or (5)). |
| `backend/tests/documents_helpers.py` | `upload_to` / `uploaded_to` / `listed_at` take a collection URL; `upload` / `uploaded` / `listed` (node) call them; `owner_files(owner, id)` added, `folder_files(node)` calls it via `owner_folder`. |
| `backend/tests/test_documents_api.py` | S006 tests: only the `write_file` monkeypatch's arguments and the `file_path` call follow the new signatures. 17 new S009 tests at the end (§ 4). |
| `backend/tests/test_removed_documents_api.py` | Three `file_store.file_path(...)` calls pass `"equipment"`; nothing else. |
| `frontend/src/components/documents/DocumentsCards.vue` | New location of `EquipmentDocuments.vue`, generalised (props, inherited groups, own/path tagging, empty states, `reload` exposed). |
| `frontend/src/components/documents/DocumentUploadModal.vue` | Moved; `basePath` and `everyUnit` props; "Visible at every unit" line. |
| `frontend/src/components/documents/DocumentTitleModal.vue` | Moved; `basePath` prop. |
| `frontend/src/components/documents/PhotoViewer.vue` | Moved; Edit/Remove only on `photo.own`; `removeNote` prop. |
| `frontend/src/views/equipment/{EquipmentDocuments,DocumentUploadModal,DocumentTitleModal,PhotoViewer}.vue` | Removed (moved, above). Moved with `mv`, not `git mv`, so nothing is staged: git shows them as deleted plus an untracked folder. |
| `frontend/src/views/EquipmentDetailView.vue` | Uses `DocumentsCards` with `basePath`; reloads it after a node edit. |
| `frontend/src/views/masters/EquipmentClassesPanel.vue` | Documents button for everyone, `documentsFor` in-panel view, header line, controls hidden while shown. |
| `frontend/src/views/masters/EquipmentTypesPanel.vue` | Same, for types. |
| `docs/steps/S009-class-type-documents/1-brief.md`, `docs/steps/README.md` | Status → In code review. |

## 4. Decisions taken

1. **Migration: the plain `MODIFY` worked.** The dev DB (MariaDB 11.4.13) accepted `MODIFY equipment_id INT NULL` with `fk_equipment_documents_equipment` in place, so the § 4 fallback (drop and re-add the FK) was not needed. All eight v7 statements were then run a second time against the migrated test DB without error (safe to re-run, as required). `SHOW CREATE TABLE` shows both new indexes used by their FKs and the CHECK.
2. **Route variable name `owner_id`.** Stacked decorators on one view need the same URL variable, so all three prefixes use `<int:owner_id>` instead of the brief's `<node_id>` / `<class_id>` / `<type_id>`. The URLs themselves are as in § 8. I checked that Werkzeug's default-redirect feature does not redirect between the three rules, because their `owner` defaults differ. The tests confirm it.
3. **`Owner` dataclass with three functions (`read`, `read_for_change`, `lock_for_change`).** The brief asks for "how to load and lock it with access". The middle function exists for the node's early scrapped check in upload step 1, which class and type don't have; for them it is the same function as `read`. The file folder is in `file_store._OWNER_FOLDERS` rather than in `OWNERS`, because § 3 gives `file_store` the owner → folder mapping. Both use the same keys.
4. **`everyUnit` is a String (`"class"`, `"type"` or `""`), not a Boolean.** The remove confirmation has to say "this class" or "this type", so the prop carries the word, and an empty string means a node. The upload dialog gets it as a Boolean. Flagged as a small departure from "true for a class or type".
5. **Reload after a node edit.** The brief says a node that changes class or type shows the new documents at once. Its `basePath` doesn't change then, so the watcher alone would not reload. `DocumentsCards` exposes `reload()`, and `EquipmentDetailView.onSaved` calls it next to the node's own reload. This avoids re-keying the component, which would revoke the PDF URLs of tabs still loading.
6. **"Managed in Masters → …" per group.** The line sits on each inherited group's heading and names the right section ("Equipment types" or "Equipment classes"), instead of one combined line. It is plain text, not a link, as the brief says.
7. **Empty states.** "No documents yet." / "No photos yet." (or "Loading…") show only when the card has nothing to list, own or inherited. With inherited items and no own ones, the card goes straight to the group headings.
8. **Item tagging.** Every item gets `path` and `own` on the client when loaded. It is a small, explicit way to give the viewer and the buttons the right URL and editability without a parallel lookup.
9. **Test helpers (adapting § 3 to the S008 layout).** The brief speaks of "the shared upload helper" in `test_documents_api.py`. Since S008, the helpers live in `backend/tests/documents_helpers.py` and the fixtures (`node`, `unit`, `at_unit`, `make_type`, …) in `conftest.py`. So the URL-taking helpers (`upload_to`, `uploaded_to`, `listed_at`, `owner_files`) went into `documents_helpers.py`, and the node versions (`upload(client, node)`, …) now call them. As a result no S006 or S008 test call had to change; only the `file_store` signature follow-ups did. The new tests are in `test_documents_api.py`, as the brief says.
10. **`collections.abc.Callable`** for the dataclass field types, not the deprecated `typing.Callable` alias.

## 5. Not done, deferred, assumed

- **Class and type documents on S008's removed-documents screen**: not done, as § 10.3 decides (queued in the README). A removed class or type document cannot be restored or deleted for good yet. S008's routes answer 404 for it.
- **New tests** (all in `test_documents_api.py`; `[x2]` = run for a class and for a type):
  - full cycle `[x2]`: upload PDF and JPEG, owner columns in the row, list without `inherited`, file, thumb, title edit, remove hides and keeps the files under the owner folder;
  - unknown class/type → 404 on every route;
  - five wrong-owner `doc_id` cases → 404;
  - inactive class: list, upload, remove;
  - inherited: type then class with `path` and label, newest first, served through `path`;
  - an empty group is absent;
  - a node without a type gets the class group only;
  - a removed class document is absent;
  - a type change through the S004 route follows;
  - operator reads but gets 403 on writes `[x2]`;
  - a user outside the node's unit: 404 on the node, 200 on its class's list and file;
  - class insert failure and storage `OSError` → 503, no file left;
  - CHECK with two owners and with none → `OperationalError` 4025 naming `chk_equipment_documents_owner`.
- **No new vitest**: no pure helper was extracted.
- **Production MariaDB version** (§ 10.5): for the user to read from Settings › Database before the release.
- **Manual browser checks (user)**, all from § 9 and none done here:
  - Masters classes/types → Documents → upload → Back;
  - the "From class/type" groups on two `RPP` nodes;
  - type change on a node;
  - photo viewer across own and inherited photos;
  - the remove wording;
  - no "No documents yet." with only class documents;
  - operator read-only in Masters;
  - a deactivated class's documents still on its machines;
  - a class PDF opened from an equipment page on Android and iPhone.

  Also worth a look: the group-heading layout on a phone width, and the Masters header line wrapping.

## Summary for the orchestrator

- **Tests**: `tooling/run-tests.bat`: backend 697 passed, frontend 36 passed (6 files). `npx vite build` built clean (no new warnings).
- **Files touched**: 16 code/test files (8 backend, 8 frontend, counting each moved component once at its new path; the 4 old paths show as deleted), plus the brief's and README's status line, plus this report.
- **Departures from the brief**:
  - route variable `owner_id` (decision 2);
  - `everyUnit` carries `"class"` / `"type"` (decision 4);
  - `reload()` exposed for node edits (decision 5);
  - the test helpers adapted to the S008 layout (decision 9).
- **Questions for the user**: none.

## Fix rounds

### Round 1

- **CR1-01 — Fixed.** `DocumentsCards.vue` has a new prop `showManagedIn` (default `false`); both "Managed in Masters → …" lines (documents and photos) now use it instead of `canEdit`. `EquipmentDetailView.vue` splits out `canEditEquipment` (`equipment:edit` alone) and passes it as `:show-managed-in`; `canEdit` is unchanged (still `canEditEquipment && !scrapped && !loading`) and still drives the node's own items. The line now shows on scrapped nodes and during reloads. The Masters panels do not pass the prop, so they show no such line (as before, they have no inherited groups).
- **CR1-02 — Fixed.** Space added after the comma in the `apiPut` call in `DocumentTitleModal.vue`.
- **Tests**: `tooling/run-tests.bat` backend and frontend green (frontend 36 passed); `npx vite build` clean.
- **Manual browser check**: as an engineer on a scrapped node with class documents, the "Managed in Masters → Equipment classes" line shows.

### Round 2

- **CR2-01 — Fixed.** Round 1 had deleted `const scrapped = computed(() => node.value?.status === "scrapped");` from `EquipmentDetailView.vue` while `canEdit` and the template (scrapped banner) still used it, so the page threw `ReferenceError`. The line is restored (as in HEAD), directly above `canEditEquipment`; `canEditEquipment` and the rest of round 1 are unchanged. I checked every identifier used in the script and template against its declaration or import (`scrapped`, `canEdit`, `canEditEquipment`, `documentsCards`, `formModal`, `moveModal`, `statusModal`, `PartsTree`, `DocumentsCards`, etc.): nothing else is undeclared.
- **Tests**: backend 697 passed, frontend 36 passed; `npx vite build` clean.
- **Manual browser check**: open an equipment page (active and scrapped node) and confirm it renders, the scrapped banner shows, and the actions are hidden when scrapped.
- Amendment A1 is only Proposed and was not implemented.
