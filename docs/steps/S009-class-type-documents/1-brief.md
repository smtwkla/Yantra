```
Step: S009 — Documents on classes and types
Doc: brief
Author: Planner (Opus)
Date: 16-10-2026 (revised 16-10-2026 after brief-reviews r1 and r2)
Status: Dropped 16-10-2026
```

# S009 — Documents on classes and types

> **Dropped 16-10-2026 by KLA.** Built and reviewed (three code-review rounds,
> clean), then dropped before commit: an equipment class or type mixes products
> of different makers (an `Extruder` class holds a new Haendle and an old Daruvar
> de-airing mill), so there is hardly anything to attach at that level.
> Manufacturer documentation belongs to the product, an equipment **model** —
> a master still to be built (queued in the README). The code was reverted to
> `c11a549`; the full diff is kept in `s009-code.patch` beside this brief, for
> the model step to reuse. Migration v7 of this step never reached production.

S006 attaches documents and photos to one node of the equipment tree. A manual
that applies to every radial piston pump then has to be uploaded to `RPP001`,
`RPP002`, … one by one, and each copy goes out of date on its own. This step
lets the same files hang on an **equipment class** or an **equipment type**, and
shows them on the page of every node of that class or type.

**Depends on:** S006 (`Done`, 76d7282) and **S008 committed** (user,
16-10-2026, § 10.3): S009 starts from S008's code. **S007** (dialog close guard) adds
`:dirty` to S006's upload and title dialogs, which this step moves to
`components/documents/`; whichever of S007 and S009 is implemented second
rebases onto the other's change to those two files (BR1-06).

Background reading:
- `docs/steps/S006-equipment-documents/1-brief.md` — all of it: this step reuses
  its rules (§ 5.2–5.8), storage (§ 6) and screens unchanged unless stated here;
- `docs/steps/S004-equipment-types-notes/1-brief.md` § 2 (ISO 14224 class/type)
  and § 6.1 (the types API, `_lock_class_for_type`);
- `backend/equipment.py` module docstring (the lock order);
- `backend/masters.py` (classes and types routes, their locks).

## 1. What will be built

1. **Documents and photos on an equipment class and on an equipment type**,
   with the S006 rules: PDF documents, JPEG/PNG/WebP photos with thumbnails, the
   same size limit, title edit, remove hides and keeps.
2. **Managed in Masters:** on **Masters → Equipment classes** and **Equipment
   types**, each row gets a **Documents** button (paperclip). It replaces the
   table, inside the same panel, with that class's or type's Documents and Photos
   cards, under a header line "← Equipment classes · RPP — Radial piston pump ·
   Documents"; the back button returns to the table. There: list, open,
   download, view photos and, with `equipment:edit`, upload, edit title and
   remove. Not a dialog: the cards open dialogs of their own, and Bootstrap
   can't stack dialogs (BR1-01).
3. **Shown on the equipment page:** the Documents and Photos cards of a node also
   list the documents of **its type** and **its class**, under the headings
   "From type *Closed execution*" and "From class *RPP — Radial piston pump*",
   after the node's own. These are **read-only** there (open, download, view);
   for editors a plain-text line says "Managed in Masters → Equipment classes /
   Equipment types" (not a link: Masters sections aren't routes). They are looked
   up live, so a node that changes class or type shows the new class's or type's
   documents at once, and an upload on a class appears on every node of that
   class.

**Out of scope:**
- moving or copying an existing node document to its class or type (re-upload it
  there and remove the node copy);
- documents per **make/model** (no model master exists; § 10.1);
- a document on a **parent** node, or on the parent's class, showing on its
  parts (each node shows its own class and type only; § 10.2);
- a documents count column in the Masters lists;
- a link from the equipment page to the right Masters section;
- class and type documents on S008's removed-documents screen (§ 10.3);
- everything S006 left out (malware scan, versioning, Office/HEIC files, …).

## 2. Standards and practice

- **EN 13460 (Maintenance — Documentation for maintenance).** The European
  standard on this step's subject. It lists the documents maintenance needs for
  an item in two groups: the **preparatory phase** — what comes with the item
  before it is used: operating and maintenance manuals, drawings, parts lists,
  test certificates — and the **operational phase** — what the plant produces
  while running it: work orders, history, condition records. Some preparatory
  documents are true for a whole product (the manufacturer's manual, the
  standard drawings), others for one serial number (its test certificate, its
  nameplate). So both levels are right: class/type documents for the first,
  node documents (S006) for the second. (EN 13306 defines the term "technical
  documentation" used here.)
- **ISO 14224 (equipment taxonomy, class → type).** ISO 14224 classifies each
  equipment unit by *class* (what it is) and, within it, *type* (how it is
  built). It defines those levels and the equipment data (Table 5:
  manufacturer, model, design data); it doesn't say where documents hang.
  Yantra attaches each document at the taxonomy level the information is true
  for: class (every `RPP`), type (every closed-execution `RPP`) or the unit
  itself.
- **ISO 55001 § 7.6.3 (2014 numbering; control of documented information).**
  Controlled information must be available where it is needed and its changes
  controlled. One controlled copy is what makes that possible: with a manual
  uploaded once on the class, a corrected edition is uploaded once and every
  machine shows it. Ten copies on ten machines are ten documents to keep in
  step, and some will not be. The S006 traceability rules (who uploaded, edited,
  removed, when; removal keeps the file) apply unchanged.
- **TPM, planned-maintenance pillar and autonomous maintenance step 3.** TPM's
  standard-condition photos and cleaning/lubrication standards are usually the
  same for every machine of a kind. Photos on a class or type are the place for
  "this is how an `RPP` should look"; one-point lessons and CIL (phase 4) can
  later point at them.
- **ISO 27001:2022.**
  - **A.8.3 (information access restriction):** node documents follow the node's
    unit access (S006). Class and type documents are **visible to every user
    with `equipment:read`, at every unit**: classes and types themselves are
    visible to everyone (`masters:read` is `*`), and their documents are generic
    (manuals, drawings of a product), not about one unit's machines. This is a
    deliberate departure from unit scoping, stated here. Files are still served
    only through permission-checked routes, never as static files.
  - **A.5.12 (classification):** the upload dialog's existing "No confidential
    documents (contracts, prices)" line covers this; for class and type uploads
    it adds "Visible at every unit".

## 3. Where

### Backend

- **Migration v7** in `backend/local_db.py`, written out in § 4, each statement
  safe to run twice (as v5 and v6), on the existing `equipment_documents`.
  Existing rows keep their `equipment_id`; no data is moved.
- **`backend/file_store.py`:** the folder becomes per **owner**:
  `owner_folder(owner, owner_id)` with `owner` one of `equipment`, `class`,
  `type` mapping to `equipment/`, `equipment-classes/`, `equipment-types/`
  under `DATA_DIR`. `file_path(owner, owner_id, name)` and
  `write_file(owner, owner_id, name, data)` take the owner; `node_folder` is
  replaced, not kept beside it. Existing node files stay where they are
  (`equipment/<node_id>/`).
- **`backend/documents.py`:** generalised from "a node" to "an owner" (§ 5.1):
  - one owner table at the top: per owner, its column (`equipment_id`,
    `class_id`, `type_id`), its file folder, its URL prefix (for the `path` of
    § 8), and how to load and lock it with access (§ 5.2);
  - the six S006 operations (list, upload, file, thumb, edit title, remove)
    written once, taking `(owner, owner_id)`. Each view carries **three stacked
    `@documents_bp.route(…, defaults={"owner": …})` decorators**, one per owner
    prefix, above its `@require_perm` (BR1-05): every URL is visible in the
    file, one endpoint per operation, no loop;
  - the blueprint's prefix becomes `/api`, the routes spell out
    `/equipment/…`, `/masters/equipment-classes/…`, `/masters/equipment-types/…`.
    The equipment URLs are unchanged;
  - the node list adds the inherited groups (§ 8). The class name for the
    heading comes from `documents.py`'s own class loader (§ 5.2), since
    `_read_node` returns only `class_code`; `_NODE_COLUMNS` is not widened;
  - the module docstring's lock note updated (§ 5.3);
  - **S008's routes** (removed list, restore, delete for good) stay node-only
    (§ 10.3) but follow the move: re-prefixed with `/equipment/` so their URLs
    don't change, and their calls follow any rename of `_lock_node_for_change`
    and the `file_store` helpers (BR2-01).
- **`backend/app.py`:** `documents_bp` registered at `/api`.
- **`backend/equipment.py`:** the docstring's note on `documents.py` updated
  (§ 5.3); nothing else.
- **`backend/tests/test_documents_api.py`:** extended (§ 9); the shared upload
  helper takes the owner's collection URL. The S006 tests keep their behaviour
  and assertions; only their calls to `file_store` helpers follow the new
  signatures (`owner_folder("equipment", id)`, `file_path("equipment", id,
  name)`, the `write_file` monkeypatch's arguments) (BR1-02). The same holds for
  S008's `test_removed_documents_api.py`, which imports the upload and folder
  helpers from `test_documents_api.py` (BR2-01).

### Frontend

- **`frontend/src/views/equipment/EquipmentDocuments.vue`** → moved and
  generalised to **`frontend/src/components/documents/DocumentsCards.vue`**:
  - props `basePath` (the documents collection URL), `canEdit`, `everyUnit`
    (true for a class or type: adds "Visible at every unit" to the upload
    dialog, and "It disappears from every machine of this class/type" to the
    remove confirmation);
  - it renders the response's own `items` (editable when `canEdit`) and, when
    the response has them, its `inherited` groups (read-only, under their
    heading). Each item's file and thumbnail URLs are its group's `path` (from
    the backend, § 8) or `basePath`, plus `/<id>/file` or `/<id>/thumb`;
  - empty states: "No documents yet." (and the photos equivalent) refers to
    the own section only and is shown only when no inherited group has items
    of that kind either;
  - its S006 blob/object-URL rules (S006 § 6.3) are unchanged.
- **`DocumentUploadModal.vue`, `DocumentTitleModal.vue`, `PhotoViewer.vue`**:
  move with it to `components/documents/`. The two dialogs take the collection
  URL (`basePath`) from the parent instead of building
  `/api/equipment/${nodeId}/documents` themselves (BR1-06). `PhotoViewer` steps
  through every photo shown (own and inherited); its Edit and Remove buttons
  show only for the owner's own photos.
- **`frontend/src/views/EquipmentDetailView.vue`:** uses `DocumentsCards` with
  `basePath = /api/equipment/<id>/documents`.
- **`EquipmentClassesPanel.vue`, `EquipmentTypesPanel.vue`:** a local
  `documentsFor` ref. The Documents button sets it to the row; while set, the
  panel shows the header line of § 1.2 and `DocumentsCards` (`basePath`
  `/api/masters/equipment-classes/<id>/documents` or `…/equipment-types/<id>/…`,
  `canEdit` from `equipment:edit`, `everyUnit`) instead of the table; Back clears
  it. The action column is rendered for everyone; only the Edit button stays
  behind `canEdit`. No new modal component. Details (BR2-02):
  - header lines: "← Equipment classes · RPP — Radial piston pump · Documents"
    and "← Equipment types · RPP — Closed execution · Documents";
  - while the documents view is shown, the card header's own controls (Show
    inactive, the class filter, Add) are hidden; Back brings them and the table
    back as they were;
  - `DocumentsCards` reloads when `basePath` changes (its watcher follows
    `basePath`, as today's follows `nodeId`), so it doesn't depend on re-keying.

### Docs

None for the coder. At approval: Plan § 4.1 and § 5 (`equipment_documents`
owners).

## 4. Data model (migration v7)

`equipment_documents` gets two more possible owners. The table keeps its name:
its rows are still documents *about equipment* — one machine, or every machine
of a class or type (§ 7).

Statements, in this order, each safe to re-run (BR1-03):

```sql
ALTER TABLE equipment_documents MODIFY equipment_id INT NULL;
ALTER TABLE equipment_documents ADD COLUMN IF NOT EXISTS class_id INT NULL AFTER equipment_id;
ALTER TABLE equipment_documents ADD COLUMN IF NOT EXISTS type_id INT NULL AFTER class_id;
-- each index before its FK, so the FK uses it rather than creating its own
ALTER TABLE equipment_documents ADD INDEX IF NOT EXISTS ix_equipment_documents_class (class_id, removed_at);
ALTER TABLE equipment_documents ADD INDEX IF NOT EXISTS ix_equipment_documents_type (type_id, removed_at);
ALTER TABLE equipment_documents ADD CONSTRAINT fk_equipment_documents_class FOREIGN KEY IF NOT EXISTS
    (class_id) REFERENCES equipment_classes (id);
ALTER TABLE equipment_documents ADD CONSTRAINT fk_equipment_documents_type FOREIGN KEY IF NOT EXISTS
    (type_id) REFERENCES equipment_types (id);
ALTER TABLE equipment_documents ADD CONSTRAINT IF NOT EXISTS chk_equipment_documents_owner
    CHECK ((equipment_id IS NOT NULL) + (class_id IS NOT NULL) + (type_id IS NOT NULL) = 1);
```

- The CHECK makes "exactly one owner" a database rule, as S002's level CHECK
  does. MariaDB enforces CHECK constraints from 10.2.1 and its grammar accepts
  `ADD CONSTRAINT IF NOT EXISTS … CHECK`; the dev DB (11.4) confirms it on the
  first run. Every v6 row has `equipment_id` set, so the CHECK holds on the data
  as it is.
- **`MODIFY` on an FK column:** relaxing `NOT NULL` → `NULL` is not a type
  change, so InnoDB is expected to accept it with `fk_equipment_documents_equipment`
  in place. If the dev DB refuses it (error 1832), the fallback is three
  statements in its place, each safe to re-run: `DROP FOREIGN KEY IF EXISTS
  fk_equipment_documents_equipment`, the `MODIFY`, then `ADD CONSTRAINT
  fk_equipment_documents_equipment FOREIGN KEY IF NOT EXISTS (equipment_id)
  REFERENCES equipment (id)`. The report says which was used.
- **Production server version:** the user reads it from Yantra's Settings ›
  Database card before the release and records it in § 10.5.
- The FKs keep a class or type with documents from being deleted; neither is
  ever deleted (masters deactivate), so nothing else changes.
- A type document has only `type_id`, not also `class_id`: a type's class never
  changes (`masters.py` `update_equipment_type` refuses a different `class_id`,
  "Class cannot be changed"), so the class is found through the type.

## 5. Rules

### 5.1 Owners

| Owner | Column | Folder under `DATA_DIR` | Read | Write |
|---|---|---|---|---|
| Node (S006) | `equipment_id` | `equipment/<id>/` | `equipment:read`, node at the user's units | `equipment:edit`, at the user's units, not scrapped |
| Class | `class_id` | `equipment-classes/<id>/` | `equipment:read` | `equipment:edit` |
| Type | `type_id` | `equipment-types/<id>/` | `equipment:read` | `equipment:edit` |

- A class or type that doesn't exist → 404.
- **Inactive** class or type: its documents are still listed, served, shown on
  its nodes' pages and editable. Inactive only stops new equipment from choosing
  it; the machines that have it still need their manuals.
- `equipment:edit` is the permission that already maintains classes and types
  (`masters.py`), so the same people maintain their documents.
- All S006 rules apply to every owner: types and size (§ 5.2), thumbnails
  (§ 5.3), titles and names (§ 5.4), remove hides and keeps (§ 5.5), writing
  safely — checks, then files with no transaction open, then a short locking
  transaction, clean-up on failure (§ 5.6), title edit (§ 5.8), serving (§ 6.2).

### 5.2 Loading and locking an owner

- **Node:** unchanged from S006 (`load_node_for_user`, lock (1), scrapped 409,
  access re-checked from the locked state — CR1-01).
- **Class:** `SELECT id, code, name, active FROM equipment_classes WHERE id = %s`
  (plain, for list and serving; `FOR UPDATE` in the write transaction). Missing →
  404.
- **Type:** the same on `equipment_types`, with its class's code and name for the
  heading (a plain join for display; the lock is on the type row alone).
- The write transactions (upload's insert, title edit, remove) lock the owner row
  first, then touch `equipment_documents`, exactly as S006 does with the node.
  For a class or type the lock has no state to decide (no scrapped), but it gives
  one order for every document write and serialises title edit with remove, as
  S006 § 5.8 relies on.

### 5.3 Lock order

- A document write takes **exactly one** owner lock — the node row (1), a class
  row (4) or a type row (5) — and then only `equipment_documents` rows, which
  nothing else locks. It never holds two owner locks. So it cannot join a cycle
  with `equipment.py` (node → … → class → type) or `masters.py` (class → type).
- The docstrings of `equipment.py` (its last bullet, today "takes lock (1)
  only") and `documents.py` say this.

### 5.4 The equipment page

- `GET /api/equipment/<node_id>/documents` (after the node's access check)
  returns, besides its own `items`, an `inherited` list: the node's **type**
  group first (when it has a type), then its **class** group, each with its
  documents not removed, newest first. A group with no documents is left out.
- A node at another unit → 404, as now; its class and type documents are then
  still reachable through the Masters routes (§ 2, A.8.3).
- Scrapped node: its own documents are read-only (S006); inherited ones are
  read-only on the equipment page anyway.
- The node's history is not written by class or type document changes (as S006).

## 6. Storage

As S006 § 6, with the owner folders of § 5.1. `stored_name` stays unique across
the whole table, so a name never collides between owners.

## 7. Design decisions

| Decision | Reason | Rejected alternative |
|---|---|---|
| Both class and type can own documents | The idea as queued; ISO 14224 has both levels, and a manual often fits one type of a class only | Class only |
| One table, three nullable owner columns + a CHECK for exactly one | Every rule, route and screen of S006 is reused; real FKs on each owner | A second table for class/type documents (copies S006's code); one `owner_kind`/`owner_id` pair (no FK possible) |
| Keep the table name `equipment_documents` | Still documents about equipment; a rename touches every query and the applied v6 for no gain | Renaming to `documents` |
| Inherited documents looked up live, not copied to nodes | One controlled copy (ISO 55001 7.6.3); a class/type change on a node shows the right set at once | Copying the file onto each node |
| Shown read-only on the equipment page, managed in Masters | Editing a class's manual from one machine's page would silently change every machine's page | Editing them from the equipment page |
| Managed in an in-panel view in Masters (BR1-01) | The cards open three dialogs of their own; Bootstrap can't stack dialogs; the row is already in hand | A dialog holding the cards; a separate route (Masters has no routes per section) |
| Class/type documents visible at every unit | Classes and types are global and their documents generic (§ 2, A.8.3) | Filtering by the units where the class is used |
| Inactive classes/types keep editable documents | Existing machines still need their manuals | Freezing them on deactivation |
| One owner lock per write | Same pattern as S006; no new lock cycle | No lock for class/type writes (title edit could race a remove) |
| One `documents.py` with an owner table and three stacked route decorators per operation (BR1-05) | No copied route bodies (DRY); every URL greppable; plain Flask | A blueprint per owner; an `add_url_rule` loop with partials |
| The backend sends each inherited group's `path` (BR1-06) | One owner → URL rule, in the backend | The frontend mapping `owner` to a URL |
| The documents cards move to `components/documents/` | Used by the equipment page and Masters | Keeping them under `views/equipment/` and importing across views |

## 8. API

Collection routes with `strict_slashes=False`, as now. For each owner prefix:

| Owner | Prefix |
|---|---|
| Node | `/api/equipment/<node_id>/documents` (unchanged) |
| Class | `/api/masters/equipment-classes/<class_id>/documents` |
| Type | `/api/masters/equipment-types/<type_id>/documents` |

the same six routes as S006 § 8, with the permissions of § 5.1:

| Method and path | Result |
|---|---|
| `GET /` | `{items, upload_max_mb}`; for a node also `inherited` (class and type lists have no `inherited` key) |
| `POST /` (multipart `kind`, `title`, `file`) | 201, the item |
| `GET /<doc_id>/file`, `GET /<doc_id>/thumb` | the file / thumbnail |
| `PUT /<doc_id>` `{title}` | 200, the item |
| `DELETE /<doc_id>` | 204 |

- A `doc_id` of another owner (another node, another class, a node's document
  through a class route, a type's document through its class's route) → 404.
- `inherited` (node list only):
  `[{"owner": "type", "id": 7, "label": "Closed execution", "path": "/api/masters/equipment-types/7/documents", "items": [...]},
  {"owner": "class", "id": 3, "label": "RPP — Radial piston pump", "path": "/api/masters/equipment-classes/3/documents", "items": [...]}]`.
  The frontend joins `path`, the item id and `/file` or `/thumb`.

## 9. Tests and acceptance

### API (`test_documents_api.py`, added to S006's)
- For a class and for a type: upload a PDF and a JPEG → 201; list; open; thumb;
  title edit; remove → 204, hidden, file kept on disk under its owner folder.
- Node list: `inherited` holds the type group, then the class group, each with
  its `path`; a group with no documents is absent; a node without a type has
  only the class group; a **removed** class document is absent from it.
- Class and type lists carry no `inherited` key.
- Change a node's type (S004 route) → its list shows the new type's documents.
- Access: an operator reads class documents (200) and can't upload (403); a
  user without access to a node's unit gets 404 on the node list but 200 on its
  class's list (the stated A.8.3 decision).
- Unknown class or type → 404; a node document through a class route, a class
  document through another class, a type document through its class's route →
  404.
- Inactive class: list, upload and remove work.
- Upload failure paths for a class (insert failure, storage `OSError` → 503):
  no file left in its folder.
- Database rule: inserting a row with two owners, or none, fails on
  `chk_equipment_documents_owner` (MariaDB error 4025, raised by PyMySQL as
  `OperationalError`, not `IntegrityError`; as
  `test_equipment_api.py::test_the_check_constraint_holds_when_the_shell_is_bypassed`).
- The S006 tests: behaviour and assertions unchanged (§ 3).

### Frontend (vitest)
- None new (no new pure helper). If the coder extracts one, it gets a test.

### Manual checks (user)
- Masters → Equipment classes → `RPP` → Documents: the table gives way to the
  cards; upload a manual PDF and a standard-condition photo; Back returns to the
  table. Open `RPP001` and another `RPP`: both show them under "From class
  RPP — …", with Open and Download and no Edit/Remove.
- Masters → Equipment types → *Closed execution* → upload a drawing. A
  closed-execution `RPP` shows it under "From type …"; an open-execution one
  doesn't. Change that node's type: the list follows.
- Photo viewer on `RPP001`: steps through its own and the inherited photos;
  Edit/Remove only on its own.
- Remove a class document: the confirmation says it disappears from every
  machine of the class.
- A node with no own documents but class documents: no "No documents yet."
- As operator: Masters → classes → Documents opens read-only.
- Deactivate a class with documents: they still show on its machines.
- Phone (Android and iPhone): open a class PDF from an equipment page.

### Acceptance
- `tooling/run-tests.bat` green; `npx vite build` clean.
- An engineer uploads the `RPP` manual once and every `RPP` page shows it.

## 10. Open questions and assumptions

1. **Decided (user, 16-10-2026): out of scope, as recommended.** Manuals are often per make/model (e.g. "11 RCE"),
   which is neither class nor type: types say how a class is built (closed /
   open execution). Recommendation: this step as briefed; where a manual fits
   one model, the engineers can create a type per model if that suits them, or
   keep it on the nodes. A model master (`make` + `model` as a list) would be a
   separate step — the register stores make and model as free text today.
2. **Decided (user, 16-10-2026) — inherited documents on parts' pages:** a
   component-unit's page shows its own class's and type's documents only, not
   those of its parent equipment or its parent's class.
3. **Decided (user, 16-10-2026): S008 first, then S009 as briefed.** S008
   (removed documents on the Settings page) lists removed documents by joining
   them to their node and unit, and its restore and delete-for-good select
   `WHERE id = %s AND equipment_id = %s`. Class and type documents have no node,
   so S008's list doesn't show them and its restore/delete answer 404 for them:
   safe, but incomplete. So a removed class or type document can't be restored
   or deleted for good until a follow-up (queued in the README: one more branch
   in S008's list, with "every unit" access for those rows). S009 still touches
   S008's code where it builds on S006's: the route prefix, the lock helper's
   name, the test helpers (§ 3, BR2-01). (Rejected: S009 also extending S008's
   list now; S009 first, with S008 revised.)
4. **Holds (checked in r1):** the S006 code-review fix CR1-01
   (`_lock_node_for_change` in the upload) is in the S006 code this step
   starts from.
5. **For the user before release:** the production MariaDB version (Settings ›
   Database), recorded here. Any 10.2.1 or later enforces the CHECK.

## 11. Amendments

### A1 — Class and type documents on the removed-documents screen

```
Requested by: KLA, 16-10-2026 ("S008 is now done, we need to bring both together")
Status: Dropped 16-10-2026 (see A2)
```

The follow-up queued at gate A (§ 10.3): S008's Settings card lists, restores
and deletes for good only **node** documents. With A1 it covers **class and
type** documents too, so a removed `RPP` manual can be brought back or erased
like any other.

#### What

1. **The removed list** (`GET /api/equipment/removed-documents`) also returns
   removed class and type documents, in the same order (`removed_at DESC, id
   DESC`), the same paging and the same `kind` and `q` filters.
2. **Restore** and **delete for good** work for class and type documents.
3. **The card** shows such a row with "Class *RPP — Radial piston pump*" or
   "Type *RPP — Closed execution*" in the Equipment column, as plain text (no
   link: Masters sections aren't routes), with no path and no scrapped state.

#### Rules

- **Who:** `equipment:purge_documents`, as S008. Class and type rows are **not
  unit-scoped**: they are visible at every unit (§ 2, A.8.3, confirmed at gate
  A), so a manager limited to some units sees every removed class and type
  document. Node rows keep S008's unit scope.
- **The list query:** a `UNION ALL` of two branches with the same columns, then
  `ORDER BY`, `LIMIT`/`OFFSET` over the union, and the `COUNT(*)` over the same
  union:
  - the **node branch** is S008's query unchanged (inner join to `equipment` +
    `NODE_JOINS`, unit scope);
  - the **class/type branch** reads documents with `class_id` or `type_id` set,
    `LEFT JOIN`s `equipment_classes` and `equipment_types` (and the type's
    class), and has no unit condition. When the user has no units at all (an
    empty set), the node branch is left out, not the whole list.
  - `q` matches, in this branch, the class code, the type name, the title and
    the original name (the node branch keeps its own: node code, title,
    original name).
- **Each item** gains `owner` (`equipment` | `class` | `type`) and `path` (the
  owner's documents collection URL, as the `inherited` groups carry it, BR1-06),
  and the card builds the action URLs as `path` + `/<id>/restore` or `/purge`.
  For a class or type item: `equipment_id`, `level`, `status`, `unit` and
  `full_path` are `null`; `code` is the class code and `name` the label above.
  Node items are unchanged apart from the two new keys.
- **Restore and purge** move to the owner pattern: three stacked route
  decorators each (§ 3), `/<owner prefix>/<int:owner_id>/documents/<int:doc_id>/restore`
  and `/purge`. The node URLs stay the same.
  - Restore: lock the owner (`lock_for_change`: a node also refuses scrapped,
    409, as S008; a class or type has no such state), then S008 § 5.2 steps 2–5
    with the owner's column.
  - Purge: lock the owner with access but **no scrapped check** (S008 § 5.3
    step 1), then S008 § 5.3 steps 2–6 with the owner's column and folder
    (`file_store.file_path(owner, owner_id, name)`). A node keeps
    `load_node_for_user(for_update=True)`; a class or type uses its plain lock.
  - The log lines name the owner ("of class 3", "of type 7") instead of "of
    node".
- **Lock order:** still exactly one owner lock per write (§ 5.3).
- The "not yet (S009 § 10.3)" comments in `documents.py` go.

#### Where

- `backend/documents.py`: the list's union and item builder; restore and purge
  generalised; docstring.
- `frontend/src/views/settings/RemovedDocuments.vue`: the class/type row
  rendering; action URLs from `path`; the Restore button disabled only for a
  scrapped **node**.
- `backend/tests/test_removed_documents_api.py`: the new cases below.

#### Tests

- A removed class document and a removed type document are listed, with
  `owner`, `path`, the label as `name` and the `null` node fields; `total`
  counts them; order by removal across node and class rows; paging across the
  union (filtered by `q`, as S008's isolation rule asks).
- `q` with the class code finds the class document and that class's node
  documents; `kind=photo` filters both branches.
- A user limited to one unit sees class and type rows but not another unit's
  node rows; a user with no units sees only class and type rows.
- Restore and purge of a class and of a type document: 200 / 204, the file gone
  from its owner folder after purge, the INFO line names the owner; purge of an
  active class document → 409; a class document through another class's or a
  node's route → 404; operator and engineer → 403.
- The S008 tests pass with behaviour and assertions unchanged.

#### Manual checks

- Remove a class document in Masters; Settings → Removed documents shows it
  as "Class RPP — …"; Restore brings it back on Masters and on every `RPP`
  page; remove it again and delete it for good.
- The same for a type document.

#### Coder model

**Opus**: transactions and locking (restore and purge generalised to three
owners) and a paged `UNION ALL` query.

#### Open points

- **Owner filter on the card** (All / Equipment / Classes / Types): not
  proposed; `q` with a class code covers it. Say if you want it.

### A2 — Drop the type owner: documents on classes only

```
Requested by: KLA, 16-10-2026 ("drop the type from this")
Status: Dropped 16-10-2026 — overtaken: the whole step was dropped (class documents removed too)
```

Documents on an equipment **type** have hardly any real use: a type says how a
class is built (pilot-operated, direct-operating), and manufacturer
documentation belongs to the product, the **model** (ISO 14224 lists the model
designation as an equipment attribute of its own; EN 13460's supplier
documentation is per product). A model master doesn't exist yet; it is queued
as its own step. So S009 keeps two owners, the **node** and the **class**.
Class documents keep their modest use: what holds for every machine of a kind,
whoever made it (an isolation procedure, a one-point lesson, standard-condition
photos).

Where this amendment and the text above disagree, this amendment wins; the text
above is not rewritten.

#### What is removed

- **Backend:** the `type` entry of `OWNERS`; the type route decorator on each of
  the six operations; the type group in the node list's `inherited`; the
  `type` → `equipment-types/` folder in `file_store`; the type lines in the
  docstrings.
- **Frontend:** the Documents button and documents view on
  **Masters → Equipment types**; the "From type …" heading code where it is
  type-specific (the generic group rendering in `DocumentsCards` stays); the
  `"type"` value of `everyUnit`.
- **Tests:** the type cases; the class cases stay. The node list's `inherited`
  then holds at most the class group.

#### Migration v8 (append-only; v7 stays as applied)

v7 is applied on the dev and test databases (never on production), so it is
not edited (CLAUDE-COMMON: migrations are append-only, user's choice (a),
16-10-2026). v8, each statement safe to run twice:

```sql
-- Rows owned by a type exist only on dev/test DBs (v7 never reached production)
DELETE FROM equipment_documents WHERE type_id IS NOT NULL;
-- The CHECK names type_id, so it goes before the column and comes back with two owners
ALTER TABLE equipment_documents DROP CONSTRAINT IF EXISTS chk_equipment_documents_owner;
ALTER TABLE equipment_documents DROP FOREIGN KEY IF EXISTS fk_equipment_documents_type;
ALTER TABLE equipment_documents DROP INDEX IF EXISTS ix_equipment_documents_type;
ALTER TABLE equipment_documents DROP COLUMN IF EXISTS type_id;
ALTER TABLE equipment_documents ADD CONSTRAINT IF NOT EXISTS chk_equipment_documents_owner
    CHECK ((equipment_id IS NOT NULL) + (class_id IS NOT NULL) = 1);
```

- **For the coder to verify on the dev DB:** whether `DROP INDEX` must come after
  `DROP FOREIGN KEY` (it does here); if MariaDB refuses any statement, say which
  and how it was reordered.
- The `DELETE` leaves a type document's file behind under
  `DATA_DIR/equipment-types/` on a dev machine: harmless, never served.
- On production, v7 and v8 run together on the first deploy; the table then has
  `equipment_id` and `class_id` only.

#### Tests

- The CHECK test: two owners, or none, still fails on
  `chk_equipment_documents_owner`.
- A migration test, if the suite has the pattern: after v8, `type_id` is gone.
- Everything else as § 9, without the type cases.

#### Manual checks

- Masters → Equipment types: no Documents button.
- An equipment page shows its own documents and "From class …" only.

#### Coder model

**Sonnet**: it only removes code along an existing pattern, plus a small
migration.

#### A1

**Dropped** (16-10-2026): the removed-documents screen gets non-node owners once,
in the model step, for class and model documents together.

## Review log

### Round 1 — `2-brief-review-r1.md` (Fable), answered 16-10-2026

| Finding | Severity | Response |
|---|---|---|
| BR1-01 Masters modal nests Bootstrap modals | major | **Accepted, option 1.** In-panel view with a `documentsFor` ref and a Back button; `MasterDocumentsModal.vue` dropped (§ 1.2, § 3, § 7, § 9). |
| BR1-02 "S006 tests unchanged" vs new `file_store` signatures | minor | **Accepted, option 1.** Reworded: behaviour and assertions unchanged, helper calls follow the new signatures; `node_folder` replaced, no shims (§ 3, § 9). |
| BR1-03 Migration details | minor | **Accepted.** v7 written out in order; indexes before FKs; CHECK grammar stated; `MODIFY` fallback; production version read by the user (§ 4, § 10.5). |
| BR1-04 EN 13460 missing; ISO 14224 over-claimed; 2014 numbering | minor | **Accepted.** EN 13460 bullet; ISO 14224 sentence softened; "(2014 numbering)" (§ 2). |
| BR1-05 `add_url_rule` loop | minor | **Accepted, option 1.** Three stacked route decorators with `defaults` per operation (§ 3, § 7). |
| BR1-06 Frontend omissions | minor | **Accepted.** Dialogs take `basePath`; backend sends each group's `path`; S007 sequencing in Depends on; action column for everyone; class name from `documents.py`'s loader (§ 3, § 7, § 8). |
| BR1-07 Three API cases | nit | **Accepted** (§ 9). |
| BR1-08 Empty state, remove wording, Masters line | nit | **Accepted.** Empty state for the own section only; `everyUnit` remove text; plain-text Masters line (§ 1.3, § 3, § 9). |

### Round 2 — `2-brief-review-r2.md` (Fable), answered 16-10-2026

All eight round-1 answers verified in the text. No blocker or major finding.

| Finding | Severity | Response |
|---|---|---|
| BR2-01 § 10.3 misses what S009 changes in S008's code; "further along" wrong | minor | **Accepted.** § 10.3 rewritten as the user's decision (a), without the wrong reason; § 3 names S008's routes, lock helper and test helpers; Depends on: S008 committed. |
| BR2-02 Masters view details | nit | **Accepted.** Both header lines; card-header controls hidden while documents show; watcher follows `basePath` (§ 3). |
| BR2-03 CHECK violation is `OperationalError` | nit | **Accepted** (§ 9). |

### User decisions, 16-10-2026

- Order: S008 first, then S009 as briefed (§ 10.3).

### Gate A — user decisions, 16-10-2026

- Per-model documents: out of scope (§ 10.1).
- Parts show their own class's and type's documents only (§ 10.2).
- Class and type documents visible at every unit: confirmed (§ 2, A.8.3).
- Approved by KLA; coded after S008 is committed. Coder: Opus.
