```
Step: S006 — Documents and photos on equipment
Doc: impl-report
Author: Coder (Opus)
Date: 16-10-2026
```

# S006 — Implementation report

Built from `1-brief.md` as approved 16-10-2026 by KLA, including the title edit
(§ 5.8) added at gate A. The brief's "QR labels (S007)" references are stale
(S007 is now the dialog close guard) and were left as they are. FormModal got only
the `saveLabel` prop; the close guard (static backdrop, discard confirm) is S007's
work and was not started.

## Tests run

- `tooling/run-tests.bat`:
  - backend **659 passed** (107 new: 46 in `test_documents_core.py`, 39 in
    `test_documents_api.py`, 22 in `test_settings_api.py`);
  - frontend **29 passed** (5 files; 3 new tests in `format.test.js`).
- `npx vite build` in `frontend/`: clean, no warnings.
- `uvx ruff check --select F` on every changed Python file: no unused or undefined
  names.

## 1. What was built

On every equipment page (equipment, component unit and component):

- **A Documents card.** It lists the PDFs, newest first, with:
  - the title;
  - the original file name, the size, and who uploaded it and when;
  - **Open**, which shows the PDF in a new tab;
  - **Download**, which saves it as `<title>.pdf`;
  - for `equipment:edit` users on a node that is not scrapped: **Edit title** (a
    pencil) and **Remove** (a bin, confirmed inline with Yes / No).
- **A Photos card.** It shows a grid of thumbnails. A click opens the **photo
  viewer**: the photo large, with previous/next, and for editors **Edit title** and
  **Remove**.
- **Add document / Add photo.** Each opens the upload dialog with kind, file and
  title.
  - The title is pre-filled from the file name.
  - A file over the limit is refused in the dialog, before it is sent.
  - The help lines carry the confidentiality note (A.5.12) and, for photos, the
  iPhone HEIC note.
  - The submit button says **Upload**.
- **Settings › Uploads.** IT admin (`settings:edit`) sets the largest upload
  (1–100 MB, default 20). A manager (`settings:read`) sees it read-only.
- **The backend:**
  - migration v6: `equipment_documents`, and the `upload_max_mb` setting seeded at
    20;
  - the API of § 8, on a new `documents` blueprint;
  - `GET`/`PUT /api/settings/app`;
  - type detection from the first bytes;
  - Pillow thumbnails with a 50 MP cap;
  - atomic file writes, a 503 when storage fails, and remove that hides without
    deleting;
  - files served only through access-checked routes, with `nosniff` and
    `Cache-Control: private`;
  - a JSON 413 backstop;
  - Flask's ceiling and Nginx's both at 101 MB.

## 2. How it works

### Backend

- **`documents_core.py`** (pure):
  - `detect_file_type` reads the signature (`%PDF-`, `FF D8 FF`, the PNG magic, or
    `RIFF…WEBP`) and returns `(type, content type)`; the client's name and type are
    never used. `FILE_TYPES` maps each type to its content type and stored extension.
  - `kind_accepts`: documents take PDF; photos take JPEG, PNG and WebP.
  - `validate_title` removes control characters, trims, and allows 1–200
    characters. `validate_document` checks the kind and the title.
  - `clean_original_name` keeps the part after the last `/` or `\`, strips
    control characters, and truncates to 255 characters (empty gives the title).
  - `stored_name`, `thumb_name` and `safe_download_name` build the file names.
  - `make_thumbnail` follows § 5.3:
    1. `Image.open(…, formats=[JPEG, PNG, WEBP])`;
    2. the size is read from the header; above 50 MP → `PhotoTooLarge`;
    3. `thumbnail((400, 400))`, then `exif_transpose`;
    4. transparency is flattened onto white with the alpha as the mask; anything
       else is `convert("RGB")`;
    5. saved as JPEG at quality 85, with no EXIF.

    An unreadable image gives `None`. Pillow's own `DecompressionBombError` also
    becomes `PhotoTooLarge`.
- **`file_store.py`** (thin I/O):
  - `node_folder` gives `DATA_DIR/equipment/<id>`, with `config.DATA_DIR` read at
    call time;
  - `write_file` creates the folder, writes to `.<name>.<8 hex>.tmp` (opened `xb`)
    in that folder, and `os.replace`s it into place; the temporary file is removed
    on error;
  - `remove_quietly` logs a failure at WARNING and never raises.
- **`documents.py`**, the upload in the order of § 5.6:
  1. `load_node_for_user` (plain read): 404 for no access, then the early 409 for a
     scrapped node; read `upload_max_mb`.
  2. `Content-Length` above the limit plus 64 KB → 400, before `request.form` is
     touched.
  3. Kind and title (400), then the file part ("Choose a file"), then
     `read(limit + 1)` (the size 400), then empty, then the type (400), then for a
     photo the thumbnail (a pixel-cap 400). A photo without a thumbnail is logged
     at WARNING with the node and the original name.
  4. Both files are written with no transaction open. An `OSError` removes what
     was written, is logged at ERROR with the path, errno and message, and becomes
     a 503.
  5. A short transaction: `LOCK_EQUIPMENT` (lock 1), the scrapped re-check from
     that locked row (409), the insert.
  6. Any failure in step 5 removes both files and re-raises the original error.
- **`documents.py`**, the other routes:
  - **Serving:** access is checked and the row must not be removed. A missing file
    on disk gives 404 "File missing", logged at ERROR. Otherwise `send_file(path,
    conditional=True, max_age=3600, download_name=<title>.<ext>)` answers inline,
    with ETag and 304. The route then adds `X-Content-Type-Options: nosniff` and
    turns `public` into `private`.
  - **Title edit:** in one transaction: lock the node (404), the scrapped check
    (409), validate the title (400 `title`; other keys ignored), `SELECT` the
    document (404), then `update_row` (title, `updated_at`, `updated_by`). The
    `SELECT` decides the 404, so saving the same title returns 200.
  - **Remove:** lock the node, the scrapped check, then the one conditional
    `UPDATE … removed_at IS NULL`; `rowcount == 0` gives 404.
  - The list and item JSON never carry `stored_name`.
- **`settings.py`:**
  - `get_setting_int(cur, key, default, min, max)` accepts ASCII digits only,
    trimmed. Anything else, or a missing row, gives the default and a WARNING.
  - `upload_max_mb(cur)` wraps it for the one setting.
  - `GET /app` (`settings:read`) returns the setting.
  - `PUT /app` (`settings:edit`) takes a JSON integer from 1 to 100 (not a
    boolean, float or string) and ignores other keys. The write happens in a
    transaction, after a `SELECT … FOR UPDATE` of the old value. An INFO line
    "Setting upload_max_mb changed by <user>: <old> -> <new>" records the change
    (A.8.15).
- **`api_common.py`:** `RequestEntityTooLarge` becomes `413 {"error": "The file
  is larger than 100 MB", "field": "file"}`.
- **`app.py`:** `MAX_CONTENT_LENGTH = (UPLOAD_MAX_MB_CEILING + 1) * MB`.

### Frontend

- **`api.js`:**
  - `apiUpload` posts a `FormData`; the browser sets the boundary.
  - `apiGetBlob` returns a `Blob`.
  - Both share the token and error handling, which was pulled out of `request`
    without changing what `request` does.
- **`EquipmentDocuments.vue`** loads `GET …/documents` on its own, and again when
  `nodeId` changes, with a sequence guard against stale answers.
  - **Thumbnails:** fetched as blobs (`/thumb`, or `/file` when `has_thumb` is
    false). Their object URLs are revoked on every reload, when the node changes
    and on unmount; an answer that arrives after a reload is revoked at once.
  - **Full photos for the viewer:** cached as promises, so two requests share one
    fetch, and revoked with the thumbnails.
  - **PDF object URLs:** kept until unmount.
  - **Open:** `window.open("", "_blank")` before any `await`, then `tab.location =
    objectUrl`. On an error the tab is closed and the message shown. When
    `window.open` returns `null`, it falls back to Download.
  - **Download:** a temporary `<a href=objectUrl download="<title>.pdf">` is
    clicked.
- **`DocumentUploadModal.vue`:**
  - kind radio buttons, preset by the button that opened the dialog;
  - a file input with `accept` set for the kind and no `capture` attribute;
    changing the kind clears the file;
  - the title is pre-filled from the file name without its extension, unless the
    user has typed their own;
  - Upload is disabled with a tooltip when there is no file or the file is over
    the limit ("Larger than N MB").
- **`DocumentTitleModal.vue`:** one field, on `FormModal` + `useFormModal`.
- **`PhotoViewer.vue`:**
  - a Bootstrap `modal-xl` with previous/next and a counter;
  - Edit title and Remove (with an inline confirm) are emitted to the parent;
  - `close()` resolves on `hidden.bs.modal`, so the title dialog opens only after
    the viewer has closed.
- **`SettingsView.vue`:** an Uploads card.

## 3. Files touched

32 files, plus this report. Of the 32, 12 are new and 20 are modified.

### Backend

| File | Change |
|---|---|
| `backend/documents_core.py` | **new**: the pure rules and the thumbnail |
| `backend/file_store.py` | **new**: folder, atomic write, quiet remove |
| `backend/documents.py` | **new**: the blueprint (list, upload, file, thumb, title edit, remove) |
| `backend/local_db.py` | migration v6 |
| `backend/config.py` | `DATA_DIR`, `UPLOAD_MAX_MB_CEILING = 100`, `MB` |
| `backend/settings.py` | `get_setting_int`, `upload_max_mb`, `GET`/`PUT /app` |
| `backend/api_common.py` | the JSON 413 handler |
| `backend/app.py` | `MAX_CONTENT_LENGTH`; registers `documents_bp` |
| `backend/equipment.py` | `_load_node_for_user` → `load_node_for_user`, `_LOCK_EQUIPMENT` → `LOCK_EQUIPMENT`; docstring lock note |
| `backend/pyproject.toml`, `backend/uv.lock` | `pillow>=12.3.0` (`uv add pillow`) |
| `backend/tests/test_documents_core.py` | **new** |
| `backend/tests/test_documents_api.py` | **new** |
| `backend/tests/test_settings_api.py` | **new** |
| `backend/tests/conftest.py` | `DATA_DIR` temporary folder (removed at session end); `equipment_documents` in `_TABLES`; fixtures `upload_limit_mb`, `db_rows`, and `user_with_units` (moved here) |
| `backend/tests/test_equipment_api.py` | `user_with_units` moved out to `conftest.py` |

### Frontend

| File | Change |
|---|---|
| `frontend/src/api.js` | `apiUpload`, `apiGetBlob`; shared `authHeaders` / `throwIfFailed` |
| `frontend/src/utils/format.js` | **new**: `formatBytes` |
| `frontend/tests/format.test.js` | **new** |
| `frontend/src/components/FormModal.vue` | the `saveLabel` prop (default "Save") |
| `frontend/src/views/equipment/EquipmentDocuments.vue` | **new**: the two cards |
| `frontend/src/views/equipment/DocumentUploadModal.vue` | **new** |
| `frontend/src/views/equipment/DocumentTitleModal.vue` | **new** |
| `frontend/src/views/equipment/PhotoViewer.vue` | **new** |
| `frontend/src/views/EquipmentDetailView.vue` | renders `EquipmentDocuments` below Notes |
| `frontend/src/views/SettingsView.vue` | the Uploads card |

### Build

| File | Change |
|---|---|
| `tooling/build/Dockerfile.backend` | `ENV DATA_DIR=/app/data`, `ENV PYTHONDONTWRITEBYTECODE=1`; Pillow comment corrected (no apt packages) |
| `tooling/build/nginx.conf` | `client_max_body_size 101M` |
| `.dockerignore` | `data/` replaces `backend/uploads/` |
| `.gitignore` | `/data/` under "Application data" |

### Docs

| File | Change |
|---|---|
| `docs/steps/S006-equipment-documents/1-brief.md` | Status → In code review |
| `docs/steps/README.md` | the S006 index row |

## 4. Decisions taken

None of these changes the brief's design; the ones that go slightly beyond its
words are marked **(beyond the brief)**.

### Backend

1. **The ceiling constant lives in `config.py`, not `app.py`.** `app.py`,
   `api_common.py` (the 413 message) and `settings.py` (the range) all need it.
   Putting it in `settings.py` would make `api_common` import `settings`, which
   imports `api_common`. `MB = 1024 * 1024` sits beside it; MB means MiB
   everywhere, as Nginx's `101M` does.
2. **`upload_max_mb(cur)` in `settings.py`** wraps
   `get_setting_int(cur, "upload_max_mb", 20, 1, 100)`, so the key, the default
   and the bounds live in one place.
3. **Response shape.**
   - `has_thumb` is a JSON boolean, not 0/1.
   - `stored_name` is never sent to the client, being a path part. It is not in
     § 8's list either.
4. **Pixel-cap messages.**
   - The cap's message gives the megapixels with at most one decimal: "64", or
     "50.4".
   - When Pillow's own bomb limit fires first, the pixel count is not known, so
     the message is "Photo too large (over 50 megapixels)".
5. **(beyond the brief) Transparency detection.** It covers `RGBA`, `LA`, `PA`,
   and any image whose `info` has `transparency`, for example an RGB PNG with a
   tRNS colour. The brief named `RGBA`, `LA` and `P` with transparency; the rule
   is the same, slightly wider.
6. **(beyond the brief) `safe_download_name` falls back to `file.<ext>`** when a
   title is nothing but quotes and slashes, so the name is never just `.pdf`.
7. **The order of checks inside the title edit.** Lock → 404 → scrapped 409 →
   title 400, the same order as `PUT /api/equipment/<id>`. So a scrapped node with
   a bad title answers 409.
8. **Upload step 4 locks through `_lock_node_for_change`**, like title edit and
   remove (changed in fix round 1, CR1-01; it first used `LOCK_EQUIPMENT`
   directly and checked access only in step 1).
9. **(beyond the brief) `PUT /api/settings/app`.**
   - Unknown keys are ignored; a missing `upload_max_mb` is a 400.
   - Every PUT is logged as "changed … old -> new", even when the value is the
     same.
   - The upsert writes `ON DUPLICATE KEY UPDATE setting_value = %s` rather than
     `VALUES()`, which MySQL deprecates.
10. **`get_setting_int` accepts ASCII digits only.** `int()` would also accept,
    for example, Arabic-Indic digits.
11. **When the file is missing.**
    - Serving checks `os.path.isfile` and then calls `send_file` with a path; a
      file object would lose the ETag.
    - If the share can't be read at that moment, the result is the same 404 "File
      missing", logged at ERROR. The brief's 503 applies to writes only.
12. **The upload route logs** a photo that got no thumbnail (WARNING), not the
    core.

### Tests

13. **Shared fixtures.**
    - `user_with_units` moved from `test_equipment_api.py` to `conftest.py`, so it
      is shared, not copied.
    - `upload_limit_mb` (it puts 20 back after each test) and `db_rows` are new
      shared fixtures.
    - `test_documents_api.py` imports the `jpeg_with_size` helper from
      `test_documents_core.py`.
14. **The at-the-cap thumbnail test checks that the photo is not refused.**
    The brief didn't ask for it. libjpeg pads a patched 10 000 × 5 000 header and
    decodes it cheaply as a draft, so the test only asserts that 50 MP exactly is
    not refused.

### Frontend

15. **`.gitignore` uses `/data/`,** anchored to the repo root, so it can't hide a
    future `data/` folder elsewhere (for example test fixtures).
16. **`api.js`.** The token and error handling were pulled out of `request()`
    into `authHeaders` and `throwIfFailed`, so `apiUpload` and `apiGetBlob` reuse
    them. `request()` behaves as before.
17. **`formatBytes` shows bytes below 1 KB** ("0 B", "999 B"), then KB or MB with
    one decimal. Anything that is not a size gives "".
18. **The upload and title dialogs call `useFormModal`'s `send()`** with their own
    request. A multipart body isn't JSON, and the page component is reused across
    nodes, so a path fixed at setup would point at the old node.
19. **Upload dialog details.**
    - Kind is chosen with radio buttons, preset by "Add document" or "Add photo".
    - Changing the kind clears the file.
    - The pre-filled title is cut to 200 characters.
    - (beyond the brief) Upload is disabled with the tooltip "Choose a file" until
      a file is chosen. The backend's "Choose a file" stays as the check that
      counts.
    - (beyond the brief) The help line also says "At most N MB".
20. **Remove confirmation** is inline Yes / No, the house pattern
    (`ActiveToggle`), not `window.confirm`.
21. **The viewer's Edit title and Remove.**
    - Bootstrap can't stack two modals, so Edit title closes the viewer first and
      then opens the title dialog.
    - Remove closes the viewer afterwards, whether it succeeded or failed, so an
      error isn't hidden behind it.
22. **Layout.**
    - Documents and Photos sit side by side (`col-lg-6`) and stack on a phone.
    - Thumbnails are 128 px tiles with the title underneath.
    - A thumbnail that fails to load shows an image icon.
23. **The Settings card.** Save is disabled while the value is unchanged, and a
    "Saved" note shows after a save. An empty box is sent as `null`, so the
    backend's range message shows.

### Not changed

24. **Pillow 12.3.0** was added with `uv add pillow`. The dev run of the app's
    import applied migration v6 to the dev database (`vel_yantra_master`), as the
    app would on start.

## 5. Not done, deferred or assumed

### Not done (out of scope, per the brief)

- QR labels;
- documents on classes or types;
- malware scanning;
- a screen for removed documents;
- HEIC;
- editing images;
- the S007 dialog close guard.

### Known and accepted

- **An orphan file is possible.** A crash between the file write and the commit
  leaves a file with no row (§ 5.6). There is no clean-up job.
- **A theoretical edge.** If two uploads ever drew the same 32-hex `stored_name`,
  `os.replace` would overwrite the first file before the unique key refused the
  second row, and the clean-up would then remove it. The chance is about 2⁻¹²⁸
  per pair, so nothing was added for it.
- **A blob URL can't be shared.** The opened PDF tab's address is a `blob:` URL;
  it can't be bookmarked or sent on.

### Manual checks for the user (the browser and the phones)

All of the brief's § 9 manual checks; none were run here:

- **On `RPP001`:** upload a PDF and two phone photos, one portrait; the
  thumbnails are upright; previous/next works in the viewer.
- **On Android and on iPhone:** "Add photo" offers the camera and the gallery;
  Open shows the PDF in a new tab; Download saves `<title>.pdf`.
- **Refusals:** a `.docx` renamed to `.pdf` is refused; a photo over the limit is
  refused in the dialog.
- **Rename:** an `IMG_…` photo renamed to "Nameplate" on the phone; the grid and
  the download name follow.
- **Remove:** the photo disappears; the equipment's history is unchanged.
- **Operator:** sees and opens documents; no Add, Edit or Remove buttons.
- **Settings:** set the limit to 5, and a 6 MB photo is refused; set 100, and a
  file just under 100 MB uploads.
- **Restart:** after a backend restart the files are still there, in the dev
  `data/` folder (created on the first upload).

### Deployment (§ 6.4) — for the user and the devops team

No file in `smtw_erp_devops` was touched.

1. **Rebuild both images.**
   - The backend image now carries Pillow and `ENV DATA_DIR` /
     `PYTHONDONTWRITEBYTECODE`.
   - The frontend image carries `nginx.conf` (`client_max_body_size 101M`).
2. **The compose file needs no change.** It already bind-mounts
   `/app-fs/Vel-Yantra-Master` at `/app/data` in backend and worker and sets
   `DATA_DIR: /app/data`. The `user: "1000:1000"` change is in the
   `smtw_erp_devops` working tree until the devops team commits it.
3. **Before or at the deploy, check the secrets file.** `secrets_app.py` is
   written `0600` and owned by `base_username`. On customer7, `id
   <base_username>` must show uid 1000. If it doesn't, the devops team makes the
   file group-readable for gid 1000. Otherwise the backend crash-loops and the
   playbook's `/api/version` check fails.
4. **After the deploy, on the VM:**
   ```
   docker compose exec backend sh -c 'touch /app/data/.w && rm /app/data/.w && echo ok'
   ```
   Then make one upload on production.
5. **Migration v6** runs on its own at start (`ensure_schema`).

### Docs left for approval time (brief § 3, "Docs")

Not edited by the coder:

- Plan § 5: the `equipment_documents` columns;
- `.claude/CLAUDE.md`: the `data/` folder and `DATA_DIR`.

## Fix rounds

### Round 1

Review: `4-code-review-r1.md`. Tests after the round: backend **660 passed**
(659 + 1 new), frontend 29 passed. No frontend change, so no `vite build`.

- **CR1-01 — Fixed.**
  - Upload step 4 now calls `_lock_node_for_change(cur, node_id)`: lock (1),
    access re-checked from the locked state (404), scrapped refused (409). The
    inline copy and the now-unused `LOCK_EQUIPMENT` import are gone. The step-5
    clean-up already removes the files on either refusal.
  - New test `TestScrapped::test_moved_to_another_unit_while_uploading_leaves_no_file`:
    after the files are written, the node is moved to another unit; the upload
    answers 404 and the node folder is empty.
  - The move is done with a plain SQL `UPDATE` through `db_rows`, not a nested
    admin API call. A nested test-client call shares Flask's `g` with the
    running request, so the outer request would turn into the admin and pass
    the access check; the test would then pass for the wrong reason.
  - Decision 8 above is updated to match.
- **CR1-02 — Rejected.** No code change; the planner has reworded the brief's
  § 9 check (photos have no Download button).
- **CR1-03 — Fixed.** Upload and title edit now read the item back inside the
  transaction (after `insert_row` / `update_row`, with the node lock still
  held) and return it after the `with` block, so a remove landing after the
  commit cannot make the response a 500. No separate test: the race needs two
  requests interleaved between commit and response, which the test client
  cannot arrange; the existing upload and title tests cover the changed path.
- **CR1-04 — Deferred.** Left at the user's choice (gate B).
- **CR1-05 — Deferred.** Left at the user's choice (gate B).
- **CR1-06 — Deferred.** Left at the user's choice (gate B).
- **CR1-07 — Deferred.** Left at the user's choice (gate B).
- **CR1-08 — Deferred.** Left at the user's choice (gate B).
