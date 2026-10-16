```
Step: S009 — Documents on classes and types
Doc: brief-review r2
Author: Brief reviewer (Fable)
Date: 16-10-2026
```

# S009 — Brief review, round 2

**Verdict: no `blocker` or `major` finding is open.** Every round-1 finding
marked `Accepted` is in the brief text, not only in the Review log (checked
one by one below). The data model, lock reasoning, access decision, API and
the in-panel Masters view all match the code they build on. What remains is
one `minor` — § 10.3 describes S008's *data* correctly but not what S009 "as
briefed" does to S008's *code* (routes, a helper, test imports), which the
coder would otherwise meet alone — and two nits.

Reviewed against HEAD `76d7282` (which contains the S006 code; the working
tree has only docs changes): `backend/documents.py`, `file_store.py`,
`local_db.py` (v5, v6, the apply loop), `equipment.py` (docstring,
`_NODE_COLUMNS`, `LOCK_EQUIPMENT`, `_LOCK_CLASS`, `_LOCK_TYPE`,
`load_node_for_user`, `_lock_type`), `masters.py`, `app.py`, `config_rbac.py`,
`auth_utils.require_perm`, `tests/test_documents_api.py`, `tests/conftest.py`
(fixtures), `tests/test_equipment_api.py` (the CHECK test); frontend
`EquipmentDocuments.vue`, `DocumentUploadModal.vue`, `DocumentTitleModal.vue`,
`PhotoViewer.vue`, `EquipmentDetailView.vue`, `EquipmentClassesPanel.vue`,
`EquipmentTypesPanel.vue`, `MastersView.vue`, `stores/masters.js`, `api.js`.
Docs: S006 brief (§ 5, § 6, § 8, § 10) and impl report; S007 brief § 1, § 3;
**S008 brief (all of it, for § 10.3)**; S004 brief § 2, § 6.1; `Plan.MD` § 4.1,
§ 5; `Maintenance-Philosophy.md`; `Plant-Facts.md`; `SMTW-WebApp-Base.md`
§ File Upload Pattern, § Flask Blueprint Pattern, § RBAC, § Form / Modal
Pattern; CLAUDE-COMMON; CLAUDE.md; `docs/steps/README.md`.

---

## Round 1 — `Accepted` responses verified in the text

| Finding | Where it now stands in the brief | Verified |
|---|---|---|
| BR1-01 in-panel view | § 1.2 (header line, Back, "Not a dialog"), § 3 Frontend (`documentsFor` ref, no new modal), § 7 row, § 9 manual checks ("the table gives way to the cards; Back returns") | yes |
| BR1-02 tests vs `file_store` signatures | § 3 Backend: `node_folder` "replaced, not kept beside it"; tests "keep their behaviour and assertions; only their calls … follow the new signatures"; the upload helper takes the collection URL; § 9 last bullet | yes |
| BR1-03 migration details | § 4: ordered statements, index before FK, CHECK grammar stated with the dev DB as the check, `MODIFY` fallback (1832), production version read by the user into § 10.5 | yes |
| BR1-04 standards | § 2: EN 13460 bullet (preparatory / operational phase), ISO 14224 "doesn't say where documents hang", "(2014 numbering)" | yes |
| BR1-05 route registration | § 3 Backend: three stacked `route(…, defaults={"owner": …})` per operation above `@require_perm`; § 7 row | yes |
| BR1-06 frontend omissions | § 3: dialogs take `basePath`; groups carry `path` (§ 3, § 8 example); S007 sequencing in **Depends on**; action column for everyone; class name from `documents.py`'s loader, `_NODE_COLUMNS` not widened | yes |
| BR1-07 three API cases | § 9: removed class document absent from `inherited`; type document through its class's route → 404; class and type lists carry no `inherited` key | yes |
| BR1-08 wording | § 3 (empty state for the own section only; `everyUnit` remove text), § 1.3 ("not a link"), § 9 manual checks | yes |

---

## Minor

### BR2-01 — minor — § 10.3 / Depends on: the S008 claims are right about the data, incomplete about the code

**Problem.** The orchestrator asked for § 10.3's claims about S008 to be
checked. The two claims it makes hold against `S008/1-brief.md`:

- "lists removed documents by joining them to their node and unit; class and
  type documents have no node, so its list would simply not show them" —
  correct: S008 § 3 / § 5.4 joins `equipment_documents` to `equipment` through
  `NODE_JOINS` (an inner join on the node), so a row with `equipment_id NULL`
  drops out; nothing errors.
- "its routes keep working because they filter on `equipment_id`" — correct:
  S008 § 5.2 step 2 and § 5.3 step 2 both select `WHERE id = %s AND
  equipment_id = %s`, so a class document's id through a node route is a 404.

What § 10.3 does not say is that **S009 "as briefed" changes three things S008
builds on**, so under option (a) the S009 coder has S008 work to do that the
brief doesn't name, and under (c) the S008 brief is wrong as written:

1. **The blueprint prefix.** S009 § 3 moves `documents_bp` from `/api/equipment`
   to `/api` and spells `/equipment/…` into the six S006 routes. S008 § 8
   registers `GET /removed-documents`, `POST /<node_id>/documents/<doc_id>/restore`
   and `…/purge` "on `documents_bp` (mounted at `/api/equipment`)". After S009
   those three rules would answer at `/api/removed-documents` and
   `/api/<node_id>/documents/…` unless the coder re-prefixes them too. S009's
   "The equipment URLs are unchanged" (§ 3) is true only for the six operations
   it lists.
2. **`_lock_node_for_change`.** S008 § 5.2 step 1 calls it for restore (and
   § 5.3 uses `load_node_for_user(for_update=True)` for purge). S009 § 3
   generalises the owner loading/locking into an owner table; whether
   `_lock_node_for_change` survives by name is the coder's choice today, and
   S008's two call sites depend on it.
3. **Test helpers.** S008 § 3 has `test_removed_documents_api.py` import
   `_upload`, `_uploaded`, `_list`, `_folder_files` and the `node`/`at_unit`
   fixtures from `test_documents_api.py`. S009 § 3 changes `_upload` to take the
   owner's collection URL and `_folder_files` to call `owner_folder("equipment",
   id)`. S008's tests would break at import or on the first call unless adapted.

Also, option (a)'s second reason — "S008 is further along" — is not accurate
on the day of writing: `S008-removed-documents/` holds only `1-brief.md` (no
review round yet), while S009 is in its second review round. The first reason
("smaller steps") stands on its own.

**Why it matters.** § 10.3 exists to settle the ordering for the user; the
coder of whichever step goes second must not meet these three points as
surprises (CLAUDE-COMMON: "Anything the brief doesn't cover is raised with the
user, not decided in code" — the coder would stop and ask).

**Options.**
1. **Add the three points to § 10.3 (recommended), one clause each:**
   - under **(a)**: "S009 then also moves S008's three routes to the `/api`
     blueprint with the `/equipment/` prefix spelled out (their URLs are
     unchanged), keeps `_lock_node_for_change(cur, node_id)` as the node
     owner's lock (or adapts S008's two call sites), and updates
     `test_removed_documents_api.py`'s calls to the shared helpers to the new
     signatures; S008's own behaviour and assertions are unchanged";
   - under **(c)**: "S008's brief is revised first: § 8 (the blueprint is at
     `/api`, routes spelled `/equipment/removed-documents` and
     `/equipment/<node_id>/documents/<doc_id>/restore|purge`) and § 3 (the
     helper signatures)";
   - replace "S008 is further along" with the state at approval, or drop it.
2. Keep § 10.3 as is and rely on the coder to notice. Not recommended.

Either way, nothing in S009's design changes.

---

## Nits

### BR2-02 — nit — § 1.2 / § 3: three Masters-view details the coder would settle alone

- **Type header line.** § 1.2 gives the class example ("← Equipment classes ·
  RPP — Radial piston pump · Documents"). For a type the natural line is
  "← Equipment types · RPP — Radial piston pump · Closed execution ·
  Documents"; the types panel already has the class name in hand through
  `equipmentClasses` (as `editType` does). One example line settles it.
- **Card header controls.** While `documentsFor` is set, the card header's
  "Show inactive" switch, the types panel's class filter and the "Add class /
  Add type" button are still rendered unless the brief says otherwise. Say
  either that they stay (harmless) or that the header shows only the title
  while the documents view is open (cleaner, and the Back button is the one
  way out).
- **Reload on a different owner.** `EquipmentDocuments.vue` reloads on
  `watch(() => props.nodeId)`. In the Masters view the same `DocumentsCards`
  instance may be shown for one class, hidden by Back, and shown again for
  another unless the panel re-keys it. Say that the watcher follows `basePath`
  (as it followed `nodeId`), or that the panel renders it with
  `:key="documentsFor.id"` inside the `v-if`. Either is a line.

### BR2-03 — nit — § 9 "Database rule" test: name the exception

MariaDB reports a CHECK violation as error **4025**, which PyMySQL raises as
`pymysql.err.OperationalError`, not `IntegrityError` (its error map has no
entry for 4025 and falls through to `OperationalError` for codes ≥ 1000). The
precedent is `test_equipment_api.py::test_the_check_constraint_holds_when_the_shell_is_bypassed`,
which asserts `caught.value.args[0] == 4025`. One clause in § 9 ("as the S002
CHECK test does") saves a failed first run.

---

## Checked and found consistent

- **S006 base.** The S006 code is committed in HEAD `76d7282` (the README index
  row still reads "In code review — awaiting user check and commit"; the index
  is updated by whoever changes the status, not by this review). § 10.4 holds:
  upload step 4, title edit and remove all go through `_lock_node_for_change`,
  and upload/title edit read the item back inside the transaction.
- **Stacked `route(…, defaults=…)` decorators (BR1-05) are safe in Flask.**
  `require_perm` uses `functools.wraps`, so the endpoint name is the view's; the
  three rules share one endpoint and one view function, which Flask allows.
  Werkzeug's `redirect_defaults` does not fire: a rule provides defaults for
  another only if `suitable_for` passes, and that fails when the matched
  `owner` value differs from the other rule's default — so
  `/api/masters/equipment-classes/3/documents` is never redirected to the
  equipment rule. `url_for` would be ambiguous, but nothing in the backend
  builds these URLs.
- **Permissions.** `equipment:read` and `masters:read` are `('*',)`;
  `equipment:edit` is `maint_engineer, it_admin` and is what
  `create/update_equipment_class` and `create/update_equipment_type` require,
  so "the same people maintain their documents" (§ 5.1) is right. `admin` is
  in no tuple; unknown keys fail closed.
- **Lock order (§ 5.3).** `equipment.py` locks (1) node → (2) parent →
  (3) unit → (4) class → (5) type → (6) serial; `masters.py` locks class → type;
  a document write takes exactly one of (1), (4), (5) and then only
  `equipment_documents` rows, which nothing else locks. The FK check on an
  insert takes a shared lock on the owner row the transaction already holds
  exclusively. No cycle. The docstring's last bullet in `equipment.py` ("takes
  lock (1) only") is the one to update, as § 5.3 says.
- **Class and type loaders (§ 5.2).** `_NODE_COLUMNS` returns `class_id`,
  `type_id`, `class_code` and `type_name` but not the class name, so the
  "RPP — Radial piston pump" label does need `documents.py`'s own class read,
  as § 3 says. `_LOCK_CLASS`/`_LOCK_TYPE` in `equipment.py` are private and lack
  `name`, so a loader of its own in `documents.py` is the plain choice.
- **Type → class is fixed.** `update_equipment_type` refuses a different
  `class_id` with 400 "Class cannot be changed", and `fk_equipment_type
  (type_id, class_id)` makes a node's type belong to its class; so a type
  document carrying only `type_id` (§ 4) is safe and the `inherited` type
  group can never be of another class.
- **"Change a node's type (S004 route)" (§ 9).** `update_equipment` accepts
  `type_id` (`_lock_type`, `newly_chosen=True`), and `conftest.py` has
  `make_type(cls=…)`, `make_class`, `make_equipment`, `user_with_units`,
  `role_client`, `db_rows` — every fixture the § 9 tests need exists.
- **Migration v7 (§ 4).** The apply loop runs each statement separately and
  records the version only after the last, so "each statement safe to run
  twice" is the right rule (as v5 and v6). `ADD COLUMN IF NOT EXISTS`,
  `ADD INDEX IF NOT EXISTS` and `ADD CONSTRAINT … FOREIGN KEY IF NOT EXISTS`
  are the forms v5 already uses. `MODIFY equipment_id INT NULL` is a complete
  definition (v6 declares `equipment_id INT NOT NULL`, no default). Every v6
  row has `equipment_id` set, so the CHECK holds on existing data. Adding each
  composite index before its FK lets InnoDB use it (leading column `class_id`
  / `type_id`) instead of creating a second one.
- **Blueprint move.** Registering `documents_bp` at `/api` with
  `/equipment/<int:owner_id>/documents` keeps the S006 URLs byte-identical;
  `/masters/equipment-classes/<id>/documents` does not collide with
  `masters_bp`'s `/equipment-classes/<id>` (PUT only, no sub-path).
- **Frontend reuse.** Document ids are unique across the one table, so the
  `thumbUrls` / `fullImages` / `pdfUrls` caches keyed by `doc.id` cannot collide
  between own and inherited items. `apiUpload(url, formData)` and
  `apiGetBlob(url)` take absolute paths, so `basePath` and the groups' `path`
  slot in. `EquipmentClassesPanel` / `EquipmentTypesPanel` have the row (code,
  name, active) in hand from `stores/masters.js`, so no new GET-by-id route is
  needed. `EquipmentDetailView`'s `canEdit` already folds in scrapped and
  loading.
- **S007 interplay (Depends on).** S007 is Approved and adds `:dirty` to
  `DocumentUploadModal.vue` and `DocumentTitleModal.vue`, which S009 moves;
  "whichever is second rebases" is the right statement. S007 also makes
  `FormModal` `backdrop: "static"`; the in-panel Masters view (BR1-01) keeps
  the three inner dialogs over a plain page, so nothing stacks.
- **Standards (§ 2).** EN 13460 is the right standard for the subject and is
  described accurately (preparatory vs operational phase documents); ISO 14224
  is now claimed only for the class/type levels and equipment data;
  ISO 55001 § 7.6.3 is "Control of documented information" in the 2014
  numbering; ISO 27001:2022 A.8.3 is "Information access restriction" and
  A.5.12 "Classification of information"; TPM autonomous-maintenance step 3 is
  the cleaning/lubrication standards step. The A.8.3 departure (class/type
  documents visible at every unit) is stated with its reason in § 2, § 5.4 and
  § 7 and tested in § 9.
- **Plan.MD.** § 4.1 ("Documents: manuals, drawings, photos attached to a piece
  of equipment") and § 5 (`equipment_documents`) are extended, not
  contradicted; the brief names both for the update at approval.
- **Scope.** No new dependency, table or permission key; per-model documents,
  parent-to-part inheritance and the removed-documents screen are correctly
  out of scope and listed.
