```
Step: S009 — Documents on classes and types
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 16-10-2026
```

# S009 — Brief review, round 1

**Verdict: one `major` finding is open (BR1-01); no `blocker`.** The data
model, the access decision, the lock reasoning and the API are sound and match
the code they build on. The one design problem is on the Masters side: the
brief puts the Documents and Photos cards — which open three Bootstrap modals
of their own — inside another Bootstrap modal, which Bootstrap does not
support and which S006 already had to work around once. The rest is five
`minor` points (a contradiction about the S006 tests, migration details to
pin down, a missing standard, the route-registration mechanism, and some
frontend omissions) and two nits.

Reviewed against the working tree (S006 implemented, uncommitted; S007 `In
review`): `backend/documents.py`, `file_store.py`, `documents_core.py`,
`local_db.py` (v1–v6), `masters.py`, `equipment.py` (docstring, `_NODE_COLUMNS`,
`LOCK_EQUIPMENT`, `_LOCK_CLASS`, `_LOCK_TYPE`, `load_node_for_user`), `app.py`,
`config_rbac.py`, `auth_utils.require_perm`, `db_helpers.py`,
`tests/test_documents_api.py`, `tests/conftest.py`; frontend
`EquipmentDocuments.vue`, `DocumentUploadModal.vue`, `DocumentTitleModal.vue`,
`PhotoViewer.vue`, `EquipmentDetailView.vue`, `FormModal.vue`,
`useFormModal.js`, `useMasterForm.js`, `MastersView.vue`,
`EquipmentClassesPanel.vue`, `EquipmentTypesPanel.vue`, `stores/masters.js`;
`tooling/dev/docker-compose.dev.yml`; `smtw_erp_devops/erp_server/yantra/
compose.yml.j2` (read-only). Docs: S006 brief, impl report and code reviews
r1–r2; S004 brief § 2, § 6.1; S007 brief § 1, § 3; `Plan.MD` § 1, § 4.1, § 5;
`Maintenance-Philosophy.md`; `Plant-Facts.md`; `SMTW-WebApp-Base.md` § File
Upload Pattern, § RBAC; CLAUDE-COMMON; CLAUDE.md.

---

## Major

### BR1-01 — major — § 3 Frontend: `MasterDocumentsModal` nests Bootstrap modals, which Bootstrap does not support

**Problem.** § 1.2 and § 3 put `DocumentsCards` inside a new Bootstrap
`modal-lg` (`MasterDocumentsModal.vue`). `DocumentsCards` (today's
`EquipmentDocuments.vue`) owns three Bootstrap modals of its own:
`DocumentUploadModal` and `DocumentTitleModal` (both on `FormModal`, which is
`Modal.getOrCreateInstance`) and `PhotoViewer` (a `modal-xl`). Every upload,
title edit or photo click from the Masters dialog would open a second modal
over the first. Bootstrap 5's documentation says "Bootstrap only supports one
modal window at a time. Nested modals aren't supported": the second backdrop
stacks at the wrong z-index, and when the inner modal closes it removes
`modal-open` from `<body>`, so the outer dialog loses its scroll lock and
backdrop behaviour. S006 met exactly this and worked around it (impl report
decision 21: "Bootstrap can't stack two modals, so Edit title closes the viewer
first and then opens the title dialog"). S007 makes `FormModal` `backdrop:
"static"` and adds a `hide.bs.modal` gate, which makes the stacking worse, not
better.

**Why it matters.** The coder would discover this mid-flight and have to pick
a different container alone — the kind of decision the brief exists to make.
The Masters dialog is the only place class and type documents can be
*managed*, so this is the step's main screen, not a corner.

**Options.**
1. **An in-panel view, not a modal (recommended).** In
   `EquipmentClassesPanel.vue` and `EquipmentTypesPanel.vue`, the Documents
   button sets a local `documentsFor` ref. While it is set, the card body
   shows a header line ("← Equipment classes" back button, then "RPP — Radial
   piston pump · Documents") and `<DocumentsCards>` in place of the table;
   Back clears it. The record is already in hand from the list (no
   `GET /equipment-classes/<id>` route exists, and none is needed), the
   panels are already re-keyed when the Masters section changes, and the
   three inner dialogs then open over a plain page as they do on the
   equipment page. `MasterDocumentsModal.vue` is dropped.
2. A route, e.g. `/masters/equipment-classes/:id/documents`, with a small
   view. Deep-linkable, but `MastersView` switches sections as local state,
   not routes, so this adds a second navigation style to Masters and needs a
   way to load one class by id.
3. Keep the modal and have `DocumentsCards` close the outer modal before
   opening an inner dialog and reopen it after (as the viewer does for the
   title dialog). Three dialogs × open/close choreography; fragile with S007's
   gate. Not recommended.

Whichever is chosen, § 1.2, § 3 (Frontend), § 7 and the § 9 manual checks
("→ Documents: opens read-only") need the same wording.

---

## Minor

### BR1-02 — minor — § 3 and § 9 say the S006 tests "pass unchanged", but § 3 changes the `file_store` signatures those tests call

**Problem.** § 3 Backend: `write_file`, `file_path` "take the owner" and
`node_folder` becomes `owner_folder(owner, owner_id)`. § 3 and § 9 then say
"The S006 tests stay and must pass unchanged." They cannot both hold:
`test_documents_api.py` calls `file_store.node_folder(node["id"])`
(`_folder_files`), `file_store.file_path(node["id"], stored)`
(`test_file_missing_on_disk_is_404`), and monkeypatches `write_file` with a
three-positional-argument replacement `fail_on_thumbnail(node_id, name, data)`
(`test_storage_error_is_503_and_leaves_nothing`). A new leading `owner`
argument breaks all three.

**Why it matters.** The coder either breaks the "unchanged" rule or keeps
`node_folder`/`file_path(node_id, …)` shims beside the owner versions to
satisfy it — two paths for one job, which is the DRY breach the brief is
trying to avoid.

**Options.**
1. **Reword (recommended):** "The S006 tests keep their behaviour and
   assertions; only their calls to `file_store` helpers follow the new
   signatures (`owner_folder("equipment", id)`, `file_path("equipment", id,
   name)`, the `write_file` monkeypatch)." Say the same for the shared
   `_upload` helper, which § 3 already generalises.
2. Keep the node helpers as one-line wrappers. Not recommended.

### BR1-03 — minor — § 4: four migration details to pin down before the coder meets them

**Problem.** The brief leaves two points "for the coder to verify" and
misses two others:

1. **Production MariaDB version.** § 4 says "prod to be confirmed by the
   coder from the devops compose". The compose
   (`smtw_erp_devops/erp_server/yantra/compose.yml.j2`) says "Database:
   MariaDB on db-server (not in this stack)" — there is no image tag to read.
   The version is on Yantra's own **Settings › Database** card in production
   (`db_status` returns `server_version`), which the user can read; the coder
   cannot. CHECK constraints are enforced from MariaDB 10.2.1, so any
   supported server passes; the brief should still name who confirms.
2. **`ADD CONSTRAINT IF NOT EXISTS … CHECK`.** MariaDB's `ALTER TABLE` grammar
   has `ADD CONSTRAINT [IF NOT EXISTS] [symbol] CHECK (expression)` — the same
   `IF NOT EXISTS` form v5 uses for its FK. The `(a IS NOT NULL) + (b IS NOT
   NULL) + (c IS NOT NULL) = 1` expression is fine (booleans are integers in
   MariaDB). The dev DB (11.4) settles this on the first run; the brief can
   state it as expected rather than open.
3. **`MODIFY equipment_id INT NULL` on a foreign-key column.** The column
   carries `fk_equipment_documents_equipment`. Relaxing NOT NULL → NULL is
   not a type change, so InnoDB should accept it with `foreign_key_checks`
   on; but MariaDB/MySQL do refuse some `MODIFY`s on FK columns (error 1832).
   Say what the fallback is if the dev DB refuses: `DROP FOREIGN KEY IF
   EXISTS`, `MODIFY`, `ADD CONSTRAINT … FOREIGN KEY IF NOT EXISTS`, each
   safe to re-run.
4. **Index before FK.** § 4 lists the FKs before the indexes. When a FK is
   added with no usable index on `class_id`, InnoDB creates one named after
   the constraint; adding `ix_equipment_documents_class (class_id,
   removed_at)` afterwards leaves both. Add each composite index **before**
   its FK (as v6 does inside `CREATE TABLE`), and the FK uses it.

**Why it matters.** Migrations are append-only; a v7 that half-applies on
production is fixed only by a v8. The cheaper place to settle these is here.

**Options.** Fold all four into § 4 as stated facts and one ordered statement
list (v5 and v6 are written out verbatim in their briefs; v7 deserves the
same). The user confirms the production server version from Settings ›
Database and records it in § 10.

### BR1-04 — minor — § 2: the standard about maintenance documentation (EN 13460) is missing; one ISO 14224 claim is too strong

**Problem.**
- **EN 13460** (*Maintenance — Documentation for maintenance*) is the
  European standard on exactly this step's subject. In plain terms it lists
  the documents maintenance needs for an item in two groups: the
  **preparatory phase** — what the manufacturer delivers before the item is
  used: operating and maintenance manuals, drawings, parts lists, test
  certificates — and the **operational phase** — what the plant produces
  while running it: work orders, history, condition records. It is the
  standard that says a plant should *have and keep* the manual and drawings
  for each item, and it is why class/type-level manuals and node-level
  certificates are both right: the manufacturer's manual is per product (the
  type or model), the test certificate is per serial number. The brief's
  argument in § 2 is correct; it just doesn't name the standard that makes it.
  EN 13306 (maintenance terminology) defines the terms "maintenance
  documentation" and "technical documentation" used there.
- **ISO 14224.** "Yantra follows the taxonomy exactly" overstates: ISO 14224
  defines the class/type levels and the equipment-data attributes
  (Table 5: manufacturer, model, design data); it does not say where
  documents hang. The accurate claim is "documents are attached at the
  taxonomy level the information is true for: class, type or unit".
- **ISO 55001 § 7.6.3.** Correct; S004 and S006 add "(2014 numbering)" and
  this brief should too, since the 2024 edition is now current.

**Why it matters.** The project owner is learning the standards from these
briefs; naming the right one and not over-claiming is the point of § 2.

**Options.** Add an EN 13460 bullet as above (three or four lines) and soften
the ISO 14224 sentence. No design change.

### BR1-05 — minor — § 3: the `add_url_rule` loop is more mechanism than the problem needs; stacked routes with `defaults` do it in plain Flask

**Problem.** § 3 registers "the six S006 operations … written once, taking
the owner; the URL rules registered per owner with `add_url_rule` in a short
explicit loop". To wire one function to three prefixes that way the coder
needs a closure or `functools.partial` per owner, an explicit endpoint name
per (owner, operation) pair (`add_url_rule` derives the endpoint from
`view_func.__name__`, which a `partial` lacks), and `require_perm` applied
inside the loop. It works, but it is the "clever" shape CLAUDE-COMMON asks to
avoid, and `grep` for a route no longer finds it.

**Options.**
1. **Stacked route decorators with `defaults` (recommended).** Flask lets one
   view carry several rules:
   ```python
   @documents_bp.route("/equipment/<int:owner_id>/documents", defaults={"owner": "equipment"}, strict_slashes=False)
   @documents_bp.route("/masters/equipment-classes/<int:owner_id>/documents", defaults={"owner": "class"}, strict_slashes=False)
   @documents_bp.route("/masters/equipment-types/<int:owner_id>/documents", defaults={"owner": "type"}, strict_slashes=False)
   @require_perm("equipment:read")
   def list_documents(owner, owner_id): ...
   ```
   Three lines per operation, eighteen in all; every URL is visible in the
   file; one endpoint per operation; no loop, no partials. (`url_for` would
   be ambiguous, but nothing in the backend builds these URLs.)
2. Keep the loop. If so, the brief should say the endpoint-naming scheme and
   that `require_perm` wraps each registered callable.

Either way, the owner table of § 3 (column, folder, loader) stays; this is
only about how the rules are registered.

### BR1-06 — minor — § 3 Frontend: omissions the coder would otherwise settle alone

**Problem.**
1. **The two dialogs need `basePath` too.** `DocumentUploadModal` and
   `DocumentTitleModal` today take `nodeId` and build
   `/api/equipment/${nodeId}/documents` themselves. § 3 says they "move with"
   the cards but not that they take the collection URL from the parent; the
   Masters use is impossible otherwise.
2. **Where a group's URL comes from.** § 3 says each inherited item's file URL
   is "built from its own group's path"; § 8 says "the frontend builds each
   group's file URLs from `owner` and `id`". The second puts an owner → URL
   table in the frontend that duplicates the backend's routing. Simpler: the
   backend puts the group's collection URL in the group
   (`"path": "/api/masters/equipment-types/7/documents"`) and the frontend
   joins `path`, the item id and `/file` or `/thumb`, as it does for its own
   `basePath`. One rule, one place.
3. **S007 touches the same two files.** S007 § 1 lists "S006's upload and
   title dialogs" among the ten dialogs that get `:dirty`. S009 moves those
   files to `components/documents/`. "No ordering needed beyond S006" (brief
   intro) is not quite right: whichever of S007 and S009 lands second rebases
   onto the other's change to these two files. Say so in **Depends on**.
4. **The Masters action column.** `EquipmentClassesPanel.vue` and
   `EquipmentTypesPanel.vue` render the action column only `v-if="canEdit"`.
   The brief's Documents button is "visible to everyone", so the column is
   always rendered and only the Edit button stays behind `canEdit`.
5. **The class label on the equipment page.** `_read_node` returns
   `class_code` but not the class name, and § 3 says `equipment.py` changes
   nothing else; so `documents.py` loads the class row itself for "RPP —
   Radial piston pump" (which § 5.2's class loader already returns). Worth one
   clause, so the coder doesn't widen `_NODE_COLUMNS`.

**Options.** Add the five points to § 3 (and 2 to § 8). All are a line each;
none changes the design.

---

## Nits

### BR1-07 — nit — § 9: three API cases worth naming

- A **removed** class document is absent from a node's `inherited` group
  (§ 5.4 says "not removed"; the tests list only own-list removal).
- A **type document asked for through its class's route** → 404 (the
  cross-owner cases listed are node-through-class and class-through-class).
- The Masters list responses carry **no `inherited` key** (so the frontend's
  "when present" branch is really exercised both ways).

### BR1-08 — nit — § 1.3 / § 5.4: three wording points for the page

- **Empty states.** `EquipmentDocuments.vue` shows "No documents yet." when
  the node's own list is empty. With inherited groups present the card is not
  empty; say that the message applies to the node's own section only (or is
  dropped when any group has items).
- **Remove confirmation on a class or type document.** "Remove this
  document?" is S006's text. For a class or type it is worth one more clause
  — "It disappears from every RPP machine's page" — since that is the whole
  point of the one-controlled-copy decision (ISO 55001 7.6.3) and the user
  may be looking at one machine's manual in their head.
- **"Managed in Masters → Equipment classes / types".** `MastersView`
  switches sections as local state, so this line cannot be a link to the
  right section; the brief should say it is plain text (or accept a link to
  `/masters` only).

---

## Checked and found consistent

- **The S006 base the brief assumes.** § 10.4's assumption holds: upload
  step 4 calls `_lock_node_for_change` (access re-checked from the locked
  state, CR1-01), as do title edit and remove. Title edit and upload read the
  item back inside the transaction (CR1-03). The S006 code review r2 left only
  a docstring nit (CR2-01) open.
- **Permissions.** `masters:read` is `('*',)` and `equipment:read` is
  `('*',)`, so "classes and types are visible to everyone" and "class/type
  documents readable by everyone with `equipment:read`" are both true as
  stated. `create_equipment_class`, `update_equipment_class`,
  `create_equipment_type`, `update_equipment_type` all require
  `equipment:edit`, so "the same people maintain their documents" is right.
  `admin` is not in any tuple; unknown keys fail closed.
- **A type's class never changes.** `update_equipment_type` refuses a
  different `class_id` with 400 "Class cannot be changed", so a type document
  carrying only `type_id` is safe, and the composite FK
  `fk_equipment_type (type_id, class_id)` makes a node's type belong to its
  class, so the `inherited` type group can never be of another class.
- **Lock order.** `equipment.py` locks node (1) → parent (2) → unit (3) →
  class (4) → type (5) → serial (6); `masters.py` locks class → type. A
  document write that takes exactly one of (1), (4) or (5) and then only
  `equipment_documents` rows (which nothing else locks) cannot complete a
  cycle. The FK checks on insert take shared locks on the owner row the same
  transaction already holds exclusively. The claim in § 5.3 is correct, and
  the `equipment.py` docstring's last bullet (today: "takes lock (1) only")
  is the one to update.
- **Existing rows and the CHECK.** Every v6 row has `equipment_id` set and
  the new columns NULL, so `chk_equipment_documents_owner` holds on the data
  as it is; no data move is needed, as § 3 says.
- **`stored_name` uniqueness across owners.** `uq_equipment_documents_stored`
  is table-wide, so a name cannot collide between folders (§ 6).
- **Inactive class or type keeps editable documents** is a deliberate
  departure from `masters.py`'s "inactive class refuses a new type" rule, and
  § 5.1 and § 7 state it with the reason. Consistent with "masters
  deactivate, never delete" (Plan § 4.1).
- **A.8.3 departure.** Stated in § 2, § 5.4 and § 7 with the reason, and
  tested in § 9 (404 on the node list, 200 on the class list). Files still
  pass only through permission-checked routes. The `Cache-Control: private`
  of S006 stays correct for class documents (harmless, and one rule).
- **Blueprint prefix.** Moving `documents_bp` to `/api` leaves the equipment
  URLs byte-identical, and its `/masters/equipment-classes/<id>/documents`
  rules do not collide with `masters_bp`'s `/equipment-classes/<id>` rules.
- **Plan.MD.** § 1 (App-FS, no MinIO) and § 4.1 ("Documents: manuals,
  drawings, photos attached to a piece of equipment") are extended, not
  contradicted; the brief's "Docs at approval" names the right rows (§ 4.1,
  § 5 `equipment_documents`).
- **Scope.** No new dependency, no new table, no new permission key; the
  removed-documents screen (S008) and per-model documents are correctly left
  out, and § 10.3 settles either order of S008/S009.
