```
Step: S009 — Documents on classes and types
Doc: code-review r2
Author: Code reviewer (Opus)
Date: 16-10-2026
```

# S009 — Code review, round 2

**Verdict: one `blocker` is open (CR2-01).** The fix for CR1-01 dropped the `scrapped`
computed from the equipment page. The page now breaks for every user with `equipment:edit`.

Reviewed:
- the whole working-tree diff against HEAD `c11a549` (`git diff -w --ignore-cr-at-eol`);
- the four moved components, against their old paths;
- `documents.py`, `DocumentsCards.vue`, `DocumentTitleModal.vue` and the script section
  of `EquipmentDetailView.vue`, read in full.

The fix round touched `DocumentsCards.vue`, `DocumentTitleModal.vue` and
`EquipmentDetailView.vue`. The modification times confirm it: the other code files predate
round 1. Brief § 11 (A1) is `Proposed`, so it is not reviewed here.

## Test results (run by the reviewer)

- `tooling/run-tests.bat`: backend **697 passed** (36.6 s), frontend vitest **36 passed**
  (6 files), exit 0.
- `npx vite build` in `frontend/`: built clean in 1.9 s, with no warnings.

Neither catches CR2-01. No vitest mounts `EquipmentDetailView`, and Vite does not reject an
undeclared identifier.

## Findings

### CR2-01 — blocker — `frontend/src/views/EquipmentDetailView.vue:39`, `:108`

**Problem.** The fix for CR1-01 removed this line from the script:

```js
const scrapped = computed(() => node.value?.status === "scrapped");
```

It was replaced by `canEditEquipment`, but two places still use `scrapped`:

- line 39: `const canEdit = computed(() => canEditEquipment.value && !scrapped.value && !loading.value);`
- line 108: `<div v-if="scrapped" …>Scrapped — this record is read-only.</div>`

The built bundle confirms it. The script compiles to a bare global,
`w.value&&!scrapped.value&&!i.value`, and the template to `N.scrapped`.

The report's Fix round 1 says "`canEdit` is unchanged (still
`canEditEquipment && !scrapped && !loading`)". The intent is right, but the declaration is
gone.

**Failure scenario.**
- **Engineer or manager** (`equipment:edit`) opens any equipment page.
  - `canEditEquipment` is true, so `scrapped.value` is evaluated and throws
    `ReferenceError: scrapped is not defined`.
  - The template's `v-else-if="canEdit"` (line 109) and the `DocumentsCards :can-edit`
    prop (line 168) both read `canEdit`, so the render fails.
  - The equipment page, the main screen of the register, does not render for anyone who
    maintains it.
- **Operator:** `&&` short-circuits on the false `canEditEquipment`, so the page renders.
  But `scrapped` is now `undefined` in the template (with a Vue warning in dev), so the
  "Scrapped — this record is read-only." banner never shows on a scrapped node. That is
  an S003 regression.

**Suggested fix.**
- Put the line back, above `canEditEquipment`:
  `const scrapped = computed(() => node.value?.status === "scrapped");`
- Then re-run the browser checks below. Check 9 (CR1-01) on a scrapped node exercises both
  the banner and the "Managed in Masters" line.

## Earlier findings

- **CR1-01: fixed in `DocumentsCards.vue`, and the fix caused CR2-01.**
  - `DocumentsCards.vue` has a new prop `showManagedIn` (default `false`), documented in
    its comment.
  - Both "Managed in Masters → …" lines use it (lines 259 and 320). `canEdit` still
    drives Add, Edit and Remove on the own items.
  - `EquipmentDetailView` passes `:show-managed-in="canEditEquipment"`, the permission
    alone. So once CR2-01 is fixed, the line shows on scrapped nodes and does not flicker
    during reloads.
  - The Masters panels leave the prop at its default. That is right, since they have no
    inherited groups.
- **CR1-02: fixed.** `DocumentTitleModal.vue:31` now has the space after the comma.

## Checked and found consistent

Unchanged since round 1, so round 1's checks still hold. I re-read `documents.py` in full
to confirm:
- **Migration v7:** the eight statements of brief § 4, in order, each idempotent,
  appended as a new version.
- **Routes:** every operation has three stacked route decorators with the `owner`
  defaults, above `@require_perm`.
  - The keys are right: `equipment:read` for list, file and thumb; `equipment:edit` for
    upload, PUT and DELETE.
  - The blueprint is at `/api`, so the node URLs are unchanged.
  - S008's routes are re-prefixed `/equipment/…` and stay node-only, as § 10.3 decides.
- **Owner column in the SQL:** it comes only from the constant `OWNERS` table, keyed by
  the route default. All values are bound parameters.
- **Locks and transactions:** each write takes exactly one owner lock, then touches only
  `equipment_documents`. The node keeps lock (1) with scrapped and access re-checked from
  the locked row.
- **Upload order (S006 § 5.6):** checks first, then the files written with no transaction
  open, then a short locking transaction. Clean-up on `BaseException`; a storage
  `OSError` gives a 503.
- **DB unavailable and dead connections:** unchanged (`get_db`).
- **Node list `inherited`:** the type group, then the class group, each with `path` from
  the backend. Empty groups are dropped and removed documents excluded. The class label
  comes from `_read_class`. Class and type lists have no `inherited` key.
- **Access (ISO 27001 A.8.3, as decided):** class and type documents need only
  `equipment:read` at every unit. Node documents keep unit access. The actor comes from
  `actor()`.
- **`DocumentsCards.vue`:**
  - its watcher follows `basePath`;
  - items are tagged with `path` and `own`;
  - Edit and Remove show on own items only, in the list and in the viewer;
  - the empty states are per kind, and show only when nothing is listed;
  - the S006 object-URL rules are kept;
  - `reload()` is exposed and called from `onSaved` after a node edit.
- **Masters panels:**
  - the `documentsFor` in-panel view has the header lines of § 3;
  - the card-header controls are hidden while the documents show;
  - Back restores the table;
  - the action column shows for everyone, with Edit still behind `canEdit`.
- **Tests** cover the brief's § 9 API list, as listed in round 1. The S006 and S008 tests
  changed only to follow the new `file_store` signatures.
- **Scope:** nothing beyond the brief. The four departures and decisions 3 and 9 are
  reported, and were accepted in round 1. Nothing of A1 is implemented.
- **Rules:** no deprecated APIs, no swallowed exceptions, comments say why, DRY.

## Manual browser checks for the user (none done here)

Run these after CR2-01 is fixed. All are from brief § 9.

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
5. **A node with no documents of its own, only class documents:** no "No documents yet."
   in the card that has inherited items.
6. **As operator:** Masters → classes → Documents opens read-only. Also, a scrapped node
   shows the "Scrapped — this record is read-only." banner (CR2-01).
7. **Deactivate a class with documents:** they still show on its machines, and stay
   editable in Masters.
8. **Phone (Android and iPhone):** open a class PDF from an equipment page. Also look at
   the group-heading layout and how the Masters header line wraps at phone width.
9. **As an engineer** (CR1-01 and CR2-01):
   - any equipment page renders, with its action buttons;
   - on a scrapped node with class documents, the page shows the scrapped banner and no
     action buttons;
   - the "Managed in Masters → Equipment classes" line shows.
