```
Step: S006 — Documents and photos on equipment
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 16-10-2026
```

# S006 — Code review, round 1

**Verdict: no `blocker` or `major` finding is open.** There are 2 `minor` findings and 6 `nit` findings.

Scope of this review: the S006 working-tree diff (read with
`git diff -w --ignore-cr-at-eol`) and the new untracked files, checked against
`1-brief.md` as approved 16-10-2026, including the § 5.8 title edit added at
gate A. These were left out as not S006 code:

- the workflow and docs edits (`.claude/**`, `docs/Plan.MD`, the README queue
  and IDE-reformatting text);
- the stale "QR labels (S007)" references in the brief;
- the S007 dialog close guard.

## Tests run

- `tooling/run-tests.bat`:
  - backend **659 passed** in 34 s;
  - frontend **29 passed** (5 files).
- `npx vite build` in `frontend/`: built clean, with no warnings.

These numbers match the impl report.

## Findings

### CR1-01 — minor — The upload's locking step re-checks scrapped but not unit access, and copies `_lock_node_for_change`

`backend/documents.py:167-174`

- **Problem:**
  - Step 4 runs `LOCK_EQUIPMENT` itself, then repeats the 404 and scrapped
    checks inline. That is `_lock_node_for_change` (lines 74-78) without its
    access check.
  - Unit access is checked only in step 1, on a plain read. Between step 1 and
    the insert come the body read, Pillow and the NFS write, which can take
    seconds.
  - Title edit and remove re-check access under the lock; upload doesn't. The
    impl report's decision 8 states this, but it leaves the three writers
    inconsistent, and the code is a near copy (DRY).
- **Failure scenario:**
  1. An engineer at unit A starts a 50 MB upload on a part.
  2. Meanwhile a manager moves the part's tree to unit B (S002 move), or
     removes the engineer's unit A.
  3. The insert still commits. A user with no access to the node has added a
     document to it, which an S002 write would refuse.

  The window is narrow, but this is the access rule (ISO 27001 A.8.3) the step
  relies on.
- **Fix:** in step 4, call `_lock_node_for_change(cur, node_id)` in place of
  lines 169-174. It locks (1), re-checks access (404) from the locked state and
  refuses scrapped (409). The step-5 clean-up already covers both refusals. Add
  one test: monkeypatch `write_file` to remove the user's unit after writing,
  then expect 404 and no files left, like `test_scrapped_while_uploading_leaves_no_file`.

### CR1-02 — minor — The brief's manual check needs a photo download name, but the page has no way to download a photo

`frontend/src/views/equipment/PhotoViewer.vue:106-131`; brief § 9 (Manual checks: "Rename a phone photo … the grid and **the download name** follow").

- **Problem:**
  - Photos can only be viewed: in the grid and in the viewer, both through
    `blob:` object URLs.
  - A long-press "Save image" on a blob image saves a file with no name, or a
    generated one, not `<title>.jpg`.
  - The backend sends the right `Content-Disposition`, and an API test asserts
    it. But no user can reach that header.
  - The impl report lists this manual check unchanged and doesn't say it can't
    be carried out. The brief is ambiguous here: § 1 lists Open/Download for
    documents only. Under the README gate rule, a point the brief doesn't cover
    goes to the user; the coder doesn't settle it silently.
- **Failure scenario:** the user follows § 9 on a phone: renames `IMG_2034` to
  "Nameplate" and looks for the download. There is no button. The check can't
  be passed, or it seems to fail.
- **Fix:** the user chooses one:
  - (a) add a **Download** button to the photo viewer, using the same
    `<a download="<title>.<ext>">` path as `downloadPdf`, with the extension
    from `content_type`. That is a small scope addition, which needs approval.
  - (b) the planner rewords the § 9 check to "the grid and the viewer title
    follow", and the impl report drops "download name" for photos.

### CR1-03 — nit — The item is read again after the commit, so a remove landing in between gives a 500

`backend/documents.py:191-192` (upload) and `:259-260` (title edit)

- **Problem:**
  - Both routes commit, then call `_read_item` on a new autocommit cursor and
    pass the result to `_item()`.
  - If another request removes the document between the commit and that read,
    `_read_item` returns `None`, and `_item(None)` raises `AttributeError`,
    which becomes a 500.
- **Failure scenario:** two editors on the same photo. One saves a new title
  while the other confirms Remove, and the remove commits in the gap. The first
  editor gets a 500 instead of the 200 their committed edit earned.
- **Fix:** read the item inside the transaction, while the node lock (1) is
  still held:
  - for the title edit, after `update_row`;
  - for the upload, after `insert_row`.

  Then return it after the `with` block. Remove already serialises on the node
  lock, so the read can't race.

### CR1-04 — nit — Small duplications

- **The scrapped message:**
  - `backend/documents.py:52` `SCRAPPED_MESSAGE` repeats the literal at
    `backend/equipment.py:500`.
  - Fix: define it once (for example in `equipment_core` beside `SCRAPPED`)
    and import it in both places.
- **The title length:**
  - `TITLE_MAX = 200` appears in `DocumentUploadModal.vue:25` and in
    `DocumentTitleModal.vue:17`.
  - Fix: one export, for example in `utils/format.js` or a small
    `documentRules.js`.
- **The setting's range:**
  - `SettingsView.vue` `UPLOAD_MAX_MB_MIN` and `UPLOAD_MAX_MB_MAX` mirror the
    backend's 1 and 100.
  - This one is display-only and acceptable. The backend's 400 message already
    states the range, so the constants could go and that message could be shown
    instead.

### CR1-05 — nit — The pixel-cap message can name the cap itself

`backend/documents_core.py:137-138, 170`

- **Problem:** `_megapixels` rounds to one decimal and drops a trailing `.0`.
- **Failure scenario:** a photo of 8165 × 6124 = 50 002 460 px is refused with
  "Photo too large (50 megapixels)", while the cap is 50. The message reads as
  self-contradictory.
- **Fix:** either:
  - round up (`math.ceil(pixels / 100_000) / 10` → "50.1"); or
  - word it as "Photo too large (50.0 megapixels; at most 50)".

### CR1-06 — nit — The API tests import a helper from another test module

`backend/tests/test_documents_api.py:14` (`from tests.test_documents_core import jpeg_with_size`)

- **Problem:**
  - pytest may load `test_documents_core` twice: once collected under its own
    module name, and once imported as `tests.test_documents_core`.
  - It also couples two test files.
  - The impl report discloses this (decision 13).
- **Fix:** move `jpeg_with_size` (and `_image_bytes`) into `conftest.py` or a
  `tests/images.py` helper module.

### CR1-07 — nit — Two access cases for the new routes are not tested

`backend/tests/test_documents_api.py:205-212`

- **Problem:** `test_another_units_node_is_404` covers list, open, upload and
  remove for an outsider. It doesn't cover:
  - the **title edit** (`PUT`) for an outsider;
  - `/thumb` for an outsider.

  Both rely on the same `load_node_for_user`, so the risk is low. The brief's
  § 9 list doesn't require them.
- **Fix:** add the two assertions to the same test. Use a photo upload so that
  `/thumb` exists.

### CR1-08 — nit — The 413 handler applies to the whole app, with a file-upload message

`backend/api_common.py:56-60`

- **Problem:**
  - Werkzeug raises `RequestEntityTooLarge` for any body over
    `MAX_CONTENT_LENGTH` on any route.
  - In Werkzeug ≥ 3.1 it also raises it for one non-file form field over
    `MAX_FORM_MEMORY_SIZE` (500 KB).
  - Every such case answers "The file is larger than 100 MB", field `file`.
- **Failure scenario:** a crafted multipart upload with a 600 KB `title`
  field gets a misleading "file is larger than 100 MB". No real client sends
  that, and nothing is unsafe.
- **Fix:** none needed now. Optionally, word the message neutrally, or check
  `request.content_length` in the handler and fall back to a generic "The
  request is too large" when the body is under the ceiling.

## Checked and found consistent

**Upload security (§ 5.2–5.4, § 6.2, A.8.28):**

- The type comes from the first bytes only (`detect_file_type`). The client's
  name and type are never used. `kind_accepts` blocks crossing kinds.
- Pillow is restricted to `formats=["JPEG","PNG","WEBP"]`.
- The 50 MP cap is checked from the header before decoding.
  `DecompressionBombError` becomes the same 400.
- `thumbnail` runs before `exif_transpose`. Transparency is flattened onto
  white with the alpha as the mask. The thumbnail carries no EXIF.
- `stored_name` is `secrets.token_hex(16)` plus the detected extension. The
  folder name is `int(node_id)`. Nothing from the client reaches a path, and
  the `../../etc/passwd.pdf` test confirms it.
- `original_name` is cleaned, and Vue escapes it. `safe_download_name` drops
  separators, quotes and control characters. `send_file` writes `filename*`.
- The size is checked three times, in the brief's order:
  1. in the dialog;
  2. `content_length` against the limit + 64 KB, before `request.form`;
  3. `read(limit + 1)`.

  A chunked request still meets check 3. The JSON 413 backstop and the
  101 MB ceilings in Flask and Nginx are both in place.
- Serving:
  - the access check, then removed → 404, and `has_thumb = 0` → 404 for
    `/thumb`;
  - a missing file → 404 "File missing", logged at ERROR;
  - `Content-Type` from the row, `inline`, `nosniff`, `private, max-age=3600`
    (no `public`), ETag/304.
  - `stored_name` never reaches the client.

**Transactions, locks and file clean-up (§ 5.5, § 5.6):**

- The upload order matches § 5.6:
  1. the plain access read and the early scrapped 409;
  2. the checks and the thumbnail, with no transaction open;
  3. the files written with no transaction (temporary file opened `xb` in the
     same folder, then `os.replace`);
  4. the short transaction: lock (1), the scrapped re-check from the locked
     row, the insert.
- The step-5 `except BaseException` removes both files and re-raises the
  original error. `remove_quietly` logs a failure and never raises.
- A storage `OSError` removes what was written, is logged at ERROR with
  `filename`/`errno`/`strerror`, and becomes a 503.
- Only lock (1) is taken, and no file I/O happens under it. The
  `equipment.py` docstring notes this.
- Remove is one conditional `UPDATE`, with `rowcount == 0` → 404, after lock
  (1) and the scrapped 409.
- Tests cover a forced insert failure, a thumbnail-write `OSError`, and the
  node being scrapped mid-upload.

**Title edit (§ 5.8):**

- The order is lock (1) with access → 404, scrapped → 409, title → 400,
  `SELECT` (id, node, not removed) → 404, `update_row` (title, `updated_at`,
  `updated_by`).
- The `SELECT` decides the 404, so saving the same title returns 200, and a
  test confirms it.
- Other keys are ignored; the `kind` in the body is tested.
- Placing the title check before the `SELECT` is reported (decision 7).

**Migration v6:**

- Append-only, with `CREATE TABLE IF NOT EXISTS` and `INSERT IGNORE`, so it is
  safe to run twice.
- The columns, types, `uq_equipment_documents_stored`,
  `ix_equipment_documents_node` and the FK match § 4. The audit convention
  (`updated_*` NULL until the first edit) and utf8mb4/InnoDB match the earlier
  tables.

**Settings (§ 5.7):**

- `get_setting_int` takes ASCII digits only and falls back to the default
  with a WARNING.
- `PUT /app`:
  - takes a JSON integer from 1 to 100; booleans, floats and strings are
    refused;
  - writes only whitelisted keys;
  - does `SELECT … FOR UPDATE`, then an upsert without the deprecated
    `VALUES()`;
  - logs the actor, the old and the new value at INFO (A.8.15).
- The permissions are `settings:read` and `settings:edit`. The limit is read
  at request time.

**RBAC and actor:**

- Every new route has `require_perm`: read routes `equipment:read`, write
  routes `equipment:edit`, settings `settings:read`/`settings:edit`.
- The actor always comes from `actor()`, the token.
- SQL is parameterised. The f-strings carry only code constants
  (`_ITEM_COLUMNS`, table names).

**DB availability:** `get_db()` raises `DBUnavailable`, which is a 503, on every
route. The pool pings on checkout.

**Frontend (§ 6.3):**

- Blobs are fetched with the token, never put in a URL.
- `openPdf` calls `window.open("", "_blank")` before the first `await`, sets
  `tab.location` to the object URL, closes the tab and shows the message on an
  error, and falls back to Download when the result is `null`.
- Download uses `<a download="<title>.pdf">`.
- Image object URLs are revoked on every reload, on a node change and on
  unmount. A late answer is revoked at once (sequence guard). The viewer's
  full-image promises are revoked too.
- PDF URLs are revoked only on unmount.
- The file input has `accept` per kind and no `capture`.
- The help lines carry the confidentiality and HEIC notes. `saveLabel` is
  "Upload".
- Upload, Edit and Remove are hidden without `equipment:edit`, and on a
  scrapped node.
- The `request()` refactor in `api.js` keeps its behaviour.

**Build and dependencies:**

- Pillow 12.3.0 is actively maintained, locked in `uv.lock`, and needs no apt
  packages.
- The Dockerfile sets `ENV DATA_DIR` and `PYTHONDONTWRITEBYTECODE`.
- `nginx.conf` has `client_max_body_size 101M`.
- `.dockerignore` has `data/`, and `.gitignore` has `/data/` (decision 15).
- Gunicorn's 120 s timeout is enough for a 100 MB write.

**Scope:**

- Everything in brief § 3 is built.
- The additions beyond the brief are all listed in "Decisions taken": 5, 6, 9,
  19, and the tests in 13 and 14.
- The only unreported gap is the photo download name (CR1-02).
- No S007 close-guard code is present.

## Manual browser checks still needed (user)

All of brief § 9; none has been run. These need particular attention:

- **iPhone Safari, Open on a PDF.** Safari can show `WebKitBlobResource error
  1` when a tab opened by `window.open` loads the opener's `blob:` URL. Confirm
  that the PDF appears. Also try the WhatsApp in-app browser, where Open should
  fall back to Download.
- **Android Chrome:**
  - Open on a PDF: the background fetch completes while the new tab has focus.
  - Download saves `<title>.pdf`, not a nameless file.
- **Opening a PDF, then leaving the equipment page while the tab still loads,
  or then using the PDF viewer's own save button.** The object URL is revoked
  on unmount, as the brief accepts. Confirm that the result is acceptable.
- **"Add photo" on both phones** offers the camera and the gallery. A portrait
  photo gives an upright thumbnail.
- **The photo viewer:** previous/next, and Edit title. The title dialog opens
  only after the viewer has closed, with no stacked backdrop. Remove from the
  viewer, both when it works and when it fails (for example, after scrapping
  the node in another tab, so the error shows on the page).
- **Upload refusals in the dialog:** a `.docx` renamed to `.pdf`; a file over
  the limit, refused before sending; a 409 for a node scrapped in another tab,
  shown at the top of the dialog.
- **Settings › Uploads:**
  - as IT admin, set 5 and then 100;
  - as a manager, the value shows read-only;
  - a 6 MB photo is refused at 5;
  - a file just under 100 MB uploads at 100.
- **As an operator:** documents and photos are visible and open, with no Add,
  Edit or Remove buttons.
- **Restart:** files survive a backend restart, in the dev `data/` folder.
- **After deploy (§ 6.4):**
  - the `secrets_app.py` uid-1000 check;
  - the write test on the VM;
  - one upload on production.
- **CR1-02:** the user decides between a photo Download button and rewording
  the check.
