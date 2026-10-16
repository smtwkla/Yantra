Step: S009 — Documents on classes and types
Doc: code-review r3
Author: Code reviewer (Opus)
Date: 16-10-2026

# S009 — Code review, round 3

**Verdict: no `blocker` or `major` finding is open.** CR2-01 is fixed. No new findings
in this round.

Reviewed:
- the whole working-tree diff against HEAD `c11a549` (`git diff -w --ignore-cr-at-eol`);
- the four moved components, diffed against their HEAD versions under `views/equipment/`;
- `EquipmentDetailView.vue`, `DocumentsCards.vue`, `PhotoViewer.vue`, both Masters panels
  and `documents.py` (owners, list, upload, serve).

Fix round 2 touched only `EquipmentDetailView.vue`, and the modification times confirm it.
The backend files predate round 1. `DocumentsCards.vue` and `DocumentTitleModal.vue` are
as they were in round 2. Brief § 11 (A1) is `Proposed`, so it is not reviewed here, and
nothing of it is implemented.

## Test results (run by the reviewer)

- `tooling/run-tests.bat`: backend **697 passed** (34.0 s), frontend vitest **36 passed**
  (6 files), exit 0.
- `npx vite build` in `frontend/`: built clean in 1.95 s, with no warnings.

## Undeclared identifiers (the gap behind CR2-01)

The build doesn't catch an undeclared identifier, so I checked it mechanically. A
throw-away script (in the session scratchpad, not in the repo) did two things for each
changed `.vue` file:
- compiled it with `@vue/compiler-sfc` in non-inline mode and listed every template
  reference that falls through to `_ctx.` (that is, one not bound by `<script setup>`);
- parsed the setup script with `@babel/parser` and listed every identifier that is read
  but never declared or imported.

To prove the check works, I ran it on a copy of `EquipmentDetailView.vue` with the
`scrapped` line removed. It reported `scrapped` in both the template and the script, which
is exactly CR2-01.

Result on the working tree:
- **Template:** none in all seven files. These are `EquipmentDetailView.vue`,
  `EquipmentClassesPanel.vue`, `EquipmentTypesPanel.vue` and the four files in
  `components/documents/`.
- **Script:** the only names reported are optional-chaining property names, which the
  quick walker does not handle (`?.status`, `?.reload`, `?.own`, `?.id`, `?.dispose`), plus
  the global `Function`. None is a free variable.
- **Imports:** `apiGet`, `apiDelete`, `apiGetBlob`, `formatBytes` and `formatDateTime`
  are all exported by `api.js`, `utils/format.js` and `utils/datetime.js`.
- **Old paths:** nothing in `frontend/src` still refers to `EquipmentDocuments`, to the
  old `views/equipment/Document*` or `PhotoViewer` paths, or to the old `nodeId` /
  `node-id` prop.

## Findings

None.

## Earlier findings

- **CR2-01: fixed.**
  - `EquipmentDetailView.vue:36` has the line back:
    `const scrapped = computed(() => node.value?.status === "scrapped");`.
  - `canEditEquipment` (line 38) and `canEdit` (line 40) are unchanged from round 1.
  - Against HEAD, the script now only adds `documentsCards` and `canEditEquipment`,
    swaps the import, and changes `onSaved`. The template only swaps the documents
    component. No identifier that HEAD declared has been removed.
- **CR1-01: fixed** (verified in round 2). `showManagedIn` is passed as
  `canEditEquipment`, so it no longer depends on scrapped or on loading.
- **CR1-02: fixed** (verified in round 2).

## Checked and found consistent

- **Moved components:** compared with HEAD, each change is one of these:
  - the `basePath` prop replaces `nodeId`;
  - the `everyUnit` line in the upload dialog;
  - `removeNote` and `editable` (`canEdit && photo.own`) in the viewer;
  - the `FormModal` import path, and comments.

  None of the S006 behaviour was dropped.
- **`DocumentsCards.vue`:**
  - every template binding is declared;
  - `Boolean(everyUnit)` uses a template global that Vue allows;
  - the watcher, the `own`/`path` tagging, the per-kind empty states and the S006
    object-URL rules are as in round 2.
- **Masters panels:**
  - `documentsFor` is declared and drives the header, the body and Back;
  - the type header uses `class_code`, which the type rows carry (the table already uses
    it);
  - the Documents button shows for everyone, and Edit stays behind `canEdit`.
- **Backend:** unchanged since round 1, so rounds 1 and 2 still hold. I re-read
  `documents.py` (owners, list, upload, serve) and confirmed:
  - the owner column comes only from the constant `OWNERS` table, and every value is a
    bound parameter;
  - each write takes exactly one owner lock;
  - the upload writes the files outside any transaction and cleans them up on
    `BaseException`;
  - the permission keys are `equipment:read` for reads and `equipment:edit` for writes.
- **Scope:** nothing beyond the brief. The README index and the brief carry
  `In code review`, and nothing of A1 is implemented.

## Manual browser checks for the user (none done here)

All are from brief § 9, plus the fix rounds.

1. **Masters → Equipment classes → `RPP` → Documents.**
   - The table gives way to the cards, with the header line.
   - Upload a manual PDF and a photo.
   - Back returns the table, with Show inactive as it was.
   - `RPP001` and another `RPP` both show them under "From class *RPP — …*", with Open and
     Download and no Edit or Remove.
2. **Masters → Equipment types → *Closed execution*.**
   - Upload a drawing.
   - A closed-execution `RPP` shows it under "From type …"; an open-execution one doesn't.
   - Change that node's type in its edit dialog: the list follows without a page reload.
3. **Photo viewer on `RPP001`:** it steps through the node's own photos and the inherited
   ones, with Edit and Remove only on its own.
4. **Remove a class document**, from the list and from the viewer: the confirmation adds
   "It disappears from every machine of this class."
5. **A node with only class documents, none of its own:** no "No documents yet." in a card
   that has inherited items.
6. **As operator:**
   - Masters → classes → Documents opens read-only;
   - a scrapped node shows the "Scrapped — this record is read-only." banner.
7. **Deactivate a class with documents:** they still show on its machines, and stay
   editable in Masters.
8. **Phone (Android and iPhone):**
   - open a class PDF from an equipment page;
   - check the group-heading layout and how the Masters header line wraps at phone width.
9. **As an engineer:**
   - any equipment page renders, with its action buttons;
   - on a scrapped node with class documents, the page shows the scrapped banner and no
     action buttons;
   - the "Managed in Masters → Equipment classes" line shows.
