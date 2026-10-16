```
Step: S009 — Documents on classes and types
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 16-10-2026
```

# S009 — Code review, round 1

**Verdict: no `blocker` or `major` finding is open.** One `minor` and one `nit`.

Reviewed: the working-tree diff against HEAD `c11a549` (`git diff -w --ignore-cr-at-eol`).
The four moved components were diffed against their old paths in HEAD
(`views/equipment/EquipmentDocuments.vue` → `components/documents/DocumentsCards.vue`;
`DocumentUploadModal`, `DocumentTitleModal`, `PhotoViewer` → `components/documents/`).
`documents.py`, `DocumentsCards.vue` and the two Masters panels were read in full.

## Test results (run by the reviewer)

- `tooling/run-tests.bat`: backend **697 passed** (39.8 s); frontend vitest **36 passed** (6 files). Exit 0.
- `npx vite build` in `frontend/`: built clean in 1.9 s, no warnings.

## Findings

### CR1-01 — minor — `frontend/src/components/documents/DocumentsCards.vue:256`, `:317` (with `EquipmentDetailView.vue:39`, `:168`)

**Problem.** The "Managed in Masters → …" line is shown when `canEdit` is true. On the
equipment page, `canEdit` is `equipment:edit && !scrapped && !loading`. That flag answers
"may this user change this node's own documents?". The brief asks a different question:
"for editors a plain-text line says …" (§ 1.3), meaning users who can maintain class and
type documents. Class documents stay editable in Masters whatever the node's status
(§ 5.1, inactive or not; § 5.4).

**Failure scenario.**
- A maintenance engineer opens a scrapped `RPP` node. They see "From class *RPP — …*"
  with no hint of where the manual is managed, although they can edit it in Masters.
- On every reload (route change, or the `reload()` after a node edit), `loading` makes the
  line disappear and come back, a small flicker.

The report doesn't list this, but it reads as a side effect of reusing `canEdit`, not a
design choice.

**Suggested fix.** Base the line on the permission alone. For example, add a
`DocumentsCards` prop `showManagedIn`. The equipment page passes
`userPermissions.includes("equipment:edit")`, and the Masters panels leave it at its
default (they have no inherited groups). Leave `canEdit` as it is for the own items.

### CR1-02 — nit — `frontend/src/components/documents/DocumentTitleModal.vue:31`

**Problem.** `apiPut(\`${props.basePath}/${editingId.value}\`,{ title: … })` has no space
after the comma. Every other call in these files has one.

**Fix.** Add the space.

## The four departures in the report

1. **`<int:owner_id>` as the route variable for all three prefixes (decision 2). Accepted.**
   Flask requires it: three rules stacked on one view must hand the same keyword
   arguments to the view. The URLs are exactly those of § 8. I checked the Werkzeug
   default-redirect concern against its rules:
   - `Rule.suitable_for` refuses a rule whose `defaults["owner"]` differs from the matched
     value, so no class or type URL gets redirected to the node rule;
   - the tests confirm it: class and type list, PUT and DELETE return 200/204, not 308.

   S008's own routes keep `<int:node_id>`, which is right: they are single rules.
2. **`everyUnit` carries `"class"` / `"type"` / `""` (decision 4). Accepted.** The remove
   note needs the word, and one prop is simpler than a Boolean plus a second string. The
   upload dialog still gets a Boolean. A side effect: `every-unit="class"` reads a little
   oddly, because the name suggests a Boolean. That is not worth a finding, since the
   brief chose the name.
3. **`DocumentsCards.reload()` after a node edit (decision 5). Accepted, and needed.**
   § 1.3 says a node that changes class or type shows the new documents "at once". After
   an edit `basePath` doesn't change, so the watcher alone would not reload. Re-keying the
   component would revoke PDF object URLs of tabs still loading (S006 § 6.3), so an
   exposed `reload()` is the least intrusive choice. The cost is one extra list fetch
   after any node edit, which is negligible.
4. **"Managed in Masters → …" on each inherited group (decision 6). Accepted.** It is
   still plain text, not a link, and it names the right section for each group. That is
   more precise than one combined line, and within the brief's wording ("Equipment
   classes / Equipment types"). The condition that shows it is CR1-01.

Decision 9 also departs from the brief's literal wording: the URL-taking helpers live in
`documents_helpers.py`, the S008 layout, rather than in `test_documents_api.py`.
Accepted: it follows where S008 moved the helpers, and it left the S006 and S008 test
calls untouched. Decision 3 (`Owner` has a `read_for_change`, and the folder map is in
`file_store`) is accepted too: it follows § 3's split, and it is reported.

## Checked and found consistent

**Migration v7.** The eight statements match § 4 one for one, in order: each index before
its FK, and the CHECK last. Each is idempotent (`IF NOT EXISTS`, and `MODIFY` re-runs as a
no-op). It is appended as a new version and v6 is untouched (append-only rule). The
`MODIFY` keeps the v6 column definition apart from the nullability.

**Owners and routes** (§ 3, § 5.1, § 8):
- Every operation has three stacked `route(…, defaults={"owner": …})` decorators above
  `@require_perm`, with the right keys: `equipment:read` for list, file and thumb;
  `equipment:edit` for upload, PUT and DELETE.
- The blueprint is at `/api`, so the node URLs are unchanged. S008's routes are
  re-prefixed with `/equipment/` and their URLs are unchanged.
- The owner column in the f-strings comes only from the constant `OWNERS` table, keyed by
  the route default and never by client input. All values are bound parameters.
- nginx `location /api/` (`client_max_body_size 101M`) also covers
  `/api/masters/…/documents`.

**Access (ISO 27001 A.8.3, as decided):**
- Node documents still go through `load_node_for_user`.
- Class and type documents need only `equipment:read` (`*`).
- A user outside the node's unit gets 404 on the node and 200 on its class (tested).
- The actor comes from `actor()`, never from the client.

**Loading and locking** (§ 5.2, § 5.3):
- The class and type reads are the brief's queries; the type read has a plain join to its
  class for the heading.
- Upload, title edit and remove each take exactly one owner lock, a single-row
  `FOR UPDATE`, and then only touch `equipment_documents`.
- The node keeps lock (1) plus the scrapped and access re-check from the locked row
  (S006 CR1-01).
- The lock-order docstrings in `documents.py` and `equipment.py` say this; (4) and (5)
  match `equipment.py`'s numbering.

**Upload order (S006 § 5.6) kept for every owner:**
- checks and the thumbnail run first;
- the files are written with no transaction open;
- then a short locking transaction inserts the row;
- clean-up on `BaseException`;
- a storage `OSError` gives a 503.

DB-unavailable (503) and dead-connection handling are unchanged (`get_db`).

**Node list `inherited`** (§ 5.4, § 8):
- the type group comes first, then the class group;
- empty groups are dropped and removed documents are excluded;
- items are newest first;
- `path` comes from the backend;
- the class label comes from `documents.py`'s `_read_class`, and `_NODE_COLUMNS` is not
  widened;
- class and type lists carry no `inherited` key.

**`file_store`:** `owner_folder` replaces `node_folder`, with no shim. `int()` on the id
and a fixed folder map mean no client text reaches a path.

**Frontend:**
- `DocumentsCards` follows `basePath` with its watcher. Own and inherited items are tagged
  with `path` and `own`; Edit and Remove show only on own items, in both the list and the
  viewer.
- The viewer steps through own photos first, then each group's. `confirmingRemove` resets
  on every photo change.
- Empty states are per kind and appear only when nothing is listed.
- The dialogs take `basePath`. The upload dialog shows "Visible at every unit", and the
  remove note "It disappears from every machine of this class/type." appears in the list
  and in the viewer.
- The S006 object-URL rules are unchanged; caches keyed by id are safe, since ids are
  unique across the table.
- **Masters panels:**
  - the `documentsFor` in-panel view has the header lines of § 3;
  - the card-header controls are hidden while the documents show;
  - Back restores the table, with its filter and switch kept;
  - the action column shows for everyone, with Edit still behind `canEdit`.

**Tests** cover the whole § 9 API list:
- for both class and type: the full cycle, and an operator gets 200 on reads and 403 on
  writes;
- unknown owner → 404 on every route;
- the five wrong-owner cases;
- an inactive class;
- inherited groups: their order, `path`, label and newest-first order;
- an empty group is absent;
- a node with no type gets the class group only;
- a removed class document is absent;
- a type change through the S004 route;
- the A.8.3 outsider case;
- class insert failure, and storage failure → 503, leaving no file;
- the CHECK violation, with two owners and with none → `OperationalError` 4025.

S006 and S008 tests: only the `file_store` signature follow-ups changed; behaviour and
assertions are as before.

**Scope:**
- Nothing is built beyond the brief.
- Out-of-scope items stay out: S008's removed list is still node-only (inner join), and
  restore and purge answer 404 for class and type documents (§ 10.3).
- The brief's and README's status lines are updated.
- `Plan.MD` already carries the S009 owner text (§ 4.1 and the `equipment_documents` row).

**Rules:**
- No deprecated APIs (`collections.abc.Callable`).
- No swallowed exceptions.
- Comments say why.
- DRY: one body per operation, and the URL helpers are shared in the tests.

## Manual browser checks for the user (none done here)

All from brief § 9:

1. **Masters → Equipment classes → `RPP` → Documents.**
   - The table gives way to the cards, with the header line.
   - Upload a manual PDF and a photo.
   - Back returns the table, with Show inactive as it was.
   - On `RPP001` and another `RPP`, both show them under "From class *RPP — …*" with Open
     and Download, and no Edit or Remove.
2. **Masters → Equipment types → *Closed execution*.**
   - Upload a drawing.
   - A closed-execution `RPP` shows it under "From type …"; an open-execution one
     doesn't.
   - Change that node's type in its edit dialog: the list follows without a page reload.
3. **Photo viewer on `RPP001`:** it steps through its own and the inherited photos, with
   Edit and Remove only on its own.
4. **Remove a class document**, from the list and from the viewer: the confirmation adds
   "It disappears from every machine of this class."
5. **A node with no own documents, only class documents:** no "No documents yet." in the
   card that has inherited items.
6. **As operator:** Masters → classes → Documents opens read-only, with no Add, Edit or
   Remove.
7. **Deactivate a class with documents:** they still show on its machines, and are still
   editable in Masters.
8. **Phone (Android and iPhone):** open a class PDF from an equipment page. Also look at
   the group-heading layout and the Masters header line wrapping at phone width.
9. **(CR1-01, after its fix)** As an engineer on a scrapped node with class documents: the
   "Managed in Masters → Equipment classes" line shows.
