```
Step: S006 — Documents and photos on equipment
Doc: brief
Author: Planner (Opus)
Date: 15-10-2026 (revised 15-10-2026 after brief-reviews r1 and r2)
Status: In review
```

# S006 — Documents and photos on equipment

Plan.MD phase 2 lists "documents" and "QR labels" as the last parts of the
equipment register. This step is documents and photos; QR labels follow as S007.

**Depends on:** S005 committed.

Background reading:
- `docs/Plan.MD` § 1 (row *Files*: App-FS NFS export, no MinIO), § 4.1, § 5
  (`equipment_documents`);
- `docs/steps/S002-equipment-register/1-brief.md` § 6 (unit access, scrapped =
  read-only, locking);
- `docs/steps/S003-equipment-screens/1-brief.md` § 4.2 (the equipment page);
- `.claude/SMTW-WebApp-Base.md` § File Upload Pattern, § Business Settings
  Pattern;
- `smtw_erp_devops/erp_server/yantra/compose.yml.j2` and `deploy.yaml` (how the
  App-FS share reaches the container; § 6.4).

## 1. What will be built

On each equipment page (any level: equipment, component-unit, component):

1. **Documents**: manuals, drawings, test certificates, as PDF files. A list with
   title, size, who uploaded it and when; **Open** shows it in a new tab,
   **Download** saves it as `<title>.pdf`.
2. **Photos**: nameplates, the machine, a part. A grid of thumbnails; click to
   see it large, with previous/next. On a phone, "Add photo" offers the camera
   or the gallery.
3. **Upload** (a dialog: kind, title, file) and **Remove**, with
   `equipment:edit`, at the user's units. Removing hides the file; it is not
   deleted (§ 5.5).
4. **An upload size limit** that IT admin sets on the **Settings** page
   (default 20 MB, range 1–100), stored in `app_settings` (§ 5.7).

**Out of scope:**
- QR labels (S007);
- photos on breakdown tickets and PM jobs (phases 3–4; they'll reuse this
  storage);
- versioning a document (a new version is a new upload; the old one can be
  removed);
- documents on classes or types (e.g. one manual for every `RPP` pump);
- Office files, DWG, HEIC photos (§ 5.2);
- malware scanning of uploads (§ 2, § 10.3);
- editing an image (crop, rotate) in the browser;
- a screen for removed documents.

## 2. Standards and practice

- **ISO 55001 § 7.5–7.6 (information requirements; documented information,
  7.6.3 control).** The asset's documents are part of its information and must
  be *controlled*: available where needed, protected, and changed in a traceable
  way. In plain terms: you can see who added or removed each document and when,
  and nothing is ever lost silently. So uploads record who and when; removal
  hides a file and records who removed it, but keeps it (§ 5.5).
- **ISO 14224 (equipment data, Table 5).** The standard expects the
  manufacturer's name, model and design data (capacity, power, …) on every
  equipment record. The manual and drawings are where those values come from,
  so keeping them with the record lets anyone verify or complete the fields
  later, and a technician at the machine has the manual on a phone.
- **TPM, autonomous maintenance (steps 1–3) and visual controls.** TPM uses
  photos: before/after photos in step 1 (initial cleaning), and photos of the
  *standard condition* in step 3 (cleaning and lubrication standards) and in
  visual controls generally, so anyone can compare the machine with how it
  should look. Photos on the equipment page are the start of that; later they
  can feed one-point lessons and CIL checklists.
- **ISO 27001:2022.**
  - **A.8.3 (information access restriction):** files are served only through a
    route that checks the user's unit access, never as plain static files.
  - **A.5.12 (classification):** like notes, documents are visible to everyone
    who can see the equipment, so the upload dialog says "No confidential
    documents (contracts, prices)".
  - **A.5.34 (privacy, PII):** phone photos carry the phone's GPS position and
    time in their EXIF data. A decision for the user (§ 10.2).
  - **A.8.6 (capacity management):** image decoding is capped so one upload
    can't exhaust the server's memory (§ 5.3).
  - **A.8.7 (protection against malware):** uploads are **not** scanned. The
    first-bytes check enforces the file *type*; it is not antivirus. Accepted
    deliberately: files come from staff and are only opened by browsers (§ 10.3).
  - **A.8.13 (backup):** files live on the App-FS share, which has its own
    backup (user, 15-10-2026).
  - **A.8.10 (information deletion)** asks that information be deleted when no
    longer needed. Here ISO 55001's control wins: a removed document is kept, as
    the record of what was attached. Real deletion (e.g. a photo uploaded by
    mistake with a person in it) would be a later admin function.
  - **A.8.28 (secure coding):** the file type is checked from the file's first
    bytes, never trusted from its name; files get system-generated names; the
    client's file name is only displayed.

## 3. Where

### Backend

- **Migration v6** in `backend/local_db.py`, each statement safe to run twice:
  - `CREATE TABLE IF NOT EXISTS equipment_documents` (§ 4);
  - `INSERT IGNORE INTO app_settings (setting_key, setting_value) VALUES ('upload_max_mb', '20')`.
- **`backend/config.py`:** `DATA_DIR = os.environ.get("DATA_DIR") or <repo>/data`.
  The env var name is `DATA_DIR` because the production compose already sets
  `DATA_DIR: /app/data` (§ 6.4).
- **`tooling/build/Dockerfile.backend`:** `ENV DATA_DIR=/app/data`, so the image
  is right even without the compose line, and `ENV PYTHONDONTWRITEBYTECODE=1`,
  since the container now runs as uid 1000 and can't write `__pycache__` under
  `/app` (§ 6.4). **No apt packages** are added: Pillow's wheels bundle libjpeg,
  zlib and libwebp (the Dockerfile's comment suggesting otherwise is updated).
- **`tooling/build/nginx.conf`:** `client_max_body_size 101M` (was `100M`), so a
  file at the 100 MB setting plus the multipart overhead still passes (§ 5.2).
- **`.dockerignore`:** `data/` replaces the template's unused `backend/uploads/`.
- **`.gitignore`:** `data/`, under its "Application data" section.
- **`backend/settings.py`** (the home of `app_settings` reads and writes, not
  `db_helpers.py`, which stays generic SQL):
  - `get_setting_int(cur, key, default, minimum, maximum)`: the first
    `app_settings` reader; a missing, non-integer or out-of-range value returns
    the default and logs a warning (an admin typo must never break uploads).
    Later steps reuse it (escalation times, Plan Q2);
  - `GET /api/settings/app` (`settings:read`) → `{upload_max_mb}`;
  - `PUT /api/settings/app` (`settings:edit`) `{upload_max_mb}`: an integer 1–100
    else 400 field `upload_max_mb`. A JSON integer only: not a boolean, a float
    or a string, as `masters_core` and `equipment_core` parse ids. Only
    whitelisted keys; one key for now. A change is logged at INFO with the actor
    and the old and new value (ISO 27001 A.8.15 logging), since `app_settings`
    has no `updated_by`.
- **`backend/documents_core.py`** (new, pure; bytes in, bytes out):
  - `detect_file_type(first_bytes)` → `("pdf" | "jpeg" | "png" | "webp", content_type)` or `None`;
  - `kind_accepts(kind, file_type)`: documents take PDF, photos take JPEG/PNG/WebP;
  - `validate_document(form)` → `(clean, errors)`: kind, title (§ 5.4);
  - `clean_original_name(raw, title)` (§ 5.4);
  - `stored_name(token, ext)`;
  - `make_thumbnail(data)` (§ 5.3). Pillow is a library, not a framework, so this
    stays pure.
- **`backend/file_store.py`** (new, thin I/O): the folder for a node, writing a
  file safely (temp name + `os.replace`), removing files, opening for serving.
  It reads `config.DATA_DIR` at call time, so tests can point it elsewhere.
- **`backend/documents.py`** (new blueprint, mounted at `/api/equipment`): the
  routes of § 8.
- **`backend/equipment.py`:** `_load_node_for_user` and `_LOCK_EQUIPMENT` become
  public (`load_node_for_user`, `LOCK_EQUIPMENT`), with the call sites renamed;
  nothing else changes in its routes. The module docstring's note on other
  modules gains: `documents.py` takes lock (1) only.
- **`backend/api_common.py`:**
  - a handler for Werkzeug's `RequestEntityTooLarge` (413) →
    `{"error": "The file is larger than 100 MB", "field": "file"}`, the number
    taken from the setting's ceiling constant. It is a backstop: the route's own
    size checks answer first (§ 5.2);
  - `documents.py` registers `uq_equipment_documents_stored` → "Retry the
    upload" in `UNIQUE_KEY_ERRORS` (as `uq_equipment_code` is).
- **`backend/app.py`:** `MAX_CONTENT_LENGTH = 101 MB` (matches Nginx's `101M`),
  from one constant that the 413 message also uses; registers the blueprint.
- **`backend/pyproject.toml`** and **`backend/uv.lock`:** Pillow (`uv add
  pillow`). Pillow is the standard Python imaging library, actively maintained
  (quarterly releases, 12.x supports Python 3.12).
- **`backend/tests/`:** `test_documents_core.py`, `test_documents_api.py`,
  `test_settings_api.py` (new) (§ 9). `conftest.py`: `equipment_documents` in
  `_TABLES`; `os.environ["DATA_DIR"]` set to a temporary folder **before**
  `import config`, next to `YANTRA_TESTING`; the folder is removed at the end of
  the session.

### Frontend

- **`frontend/src/api.js`:** `apiUpload(url, formData)` (no JSON content type)
  and `apiGetBlob(url)`.
- **`frontend/src/utils/format.js`** (new, pure): `formatBytes(n)` (KB/MB, one
  decimal), with a vitest file.
- **`frontend/src/components/FormModal.vue`:** a `saveLabel` prop, default
  "Save"; the upload dialog uses "Upload".
- **`frontend/src/views/equipment/EquipmentDocuments.vue`** (new): the Documents
  and Photos cards.
- **`frontend/src/views/equipment/DocumentUploadModal.vue`** (new): the upload
  dialog.
- **`frontend/src/views/equipment/PhotoViewer.vue`** (new): a Bootstrap modal
  showing one photo large, with previous/next.
- **`frontend/src/views/EquipmentDetailView.vue`:** the new component **below the
  Notes card** (or below Details / Parts / History when there are no notes).
- **`frontend/src/views/SettingsView.vue`:** an "Uploads" card: the limit, editable
  with `settings:edit`, read-only with `settings:read`.

### Docs

None for the coder. At approval: Plan § 5 (`equipment_documents` columns), and
`.claude/CLAUDE.md` (the `data/` folder and `DATA_DIR`). The coder writes the
deployment lines of § 6.4 into the report.

## 4. Data model (migration v6)

**`equipment_documents`**

| Column | Type / rule |
|---|---|
| `id` | `INT AUTO_INCREMENT PRIMARY KEY` |
| `equipment_id` | `INT NOT NULL`, `fk_equipment_documents_equipment` → `equipment` |
| `kind` | `ENUM('document','photo') NOT NULL` |
| `title` | `VARCHAR(200) NOT NULL` |
| `original_name` | `VARCHAR(255) NOT NULL`: the client's file name, cleaned, display only |
| `stored_name` | `VARCHAR(80) NOT NULL`: system-generated, `uq_equipment_documents_stored` |
| `content_type` | `VARCHAR(50) NOT NULL`: from the detected type |
| `size_bytes` | `INT NOT NULL` |
| `has_thumb` | `TINYINT(1) NOT NULL DEFAULT 0` |
| `created_at`, `created_by` | audit, as S001 |
| `removed_at`, `removed_by` | `NULL` until removed |

- Index `ix_equipment_documents_node (equipment_id, removed_at)`.
- No `updated_*`: a document isn't edited (§ 10.4).

## 5. Rules

### 5.1 Who and where

| Action | Permission | Also |
|---|---|---|
| List, open, view | `equipment:read` | the node is at the user's units (S002), else 404 |
| Upload, remove | `equipment:edit` | the node is at the user's units; not scrapped (409, the S002 read-only rule) |
| Read the upload limit | `settings:read` | |
| Change the upload limit | `settings:edit` (IT admin) | |

### 5.2 File types and size

- **Accepted**, detected from the file's first bytes:
  - document: **PDF**;
  - photo: **JPEG, PNG, WebP**.

  A type the kind doesn't accept, or anything else → 400, field `file`, "Only PDF
  documents and JPEG, PNG or WebP photos". The client's extension and content
  type are ignored.
- **HEIC** (iPhone's own format): refused by the rule above. The camera path
  works anyway, because Safari converts camera photos to JPEG when the file
  input doesn't list HEIC. The dialog's help line says: "iPhone photos shared
  from Files or WhatsApp: set Camera › Formats › Most Compatible, or share as
  JPEG." Reading HEIC would need another library (`pillow-heif`); not now.
- **Size**, checked three times:
  1. **In the dialog:** the list response carries `upload_max_mb` (§ 8); a file
     above it is refused before sending ("Larger than N MB"), saving mobile data.
  2. **Before parsing:** the route compares `request.content_length` with
     `upload_max_mb` MB plus 64 KB for the form fields, **before** touching
     `request.files` (Werkzeug spools the whole body on first access) → 400
     field `file`, "The file is larger than N MB". When `content_length` is
     missing (a chunked request; browsers don't send those for a form), this
     check is skipped and check 3 still applies.
  3. **After parsing:** `file.read(limit + 1)`; more than `limit` bytes → the same
     400. (`+ 1` tells "exactly at the limit" from "over it".)
  - **Ceilings:** the setting's maximum is 100 MB; Flask's `MAX_CONTENT_LENGTH`
    and Nginx's `client_max_body_size` are **101 MB**, so a 100 MB file plus the
    multipart overhead passes both. Werkzeug enforces `MAX_CONTENT_LENGTH` only
    when `request.files` is read, after check 2, so the 413 handler is a
    backstop; Nginx's own 413 page (above 101 MB) stays HTML.
  - Memory per request stays at most the limit: Werkzeug spools the body to a
    temporary file on disk. Checked as fine for three workers.
- An empty file → 400 field `file`, "The file is empty". A missing file part →
  400 field `file`, "Choose a file".

### 5.3 Thumbnails (photos)

`make_thumbnail(data) -> bytes | None` in `documents_core.py`:
1. `Image.open(BytesIO(data), formats=["JPEG", "PNG", "WEBP"])`, so a file
   whose first bytes say JPEG can't reach any other Pillow decoder.
2. **Pixel cap:** read the size from the header (no decoding yet); above
   **50 megapixels** → raise a refusal that the route turns into 400 field
   `file`, "Photo too large (N megapixels)". Phones take 12 MP photos by
   default, 48 MP at most. Pillow raises its own `DecompressionBombError` from
   `Image.open` above about 179 MP; that is also turned into this 400, as a
   backstop.
3. `thumbnail((400, 400))` **first** (for JPEG it decodes at a reduced scale,
   so a 12 MP photo never decodes in full), **then** `ImageOps.exif_transpose`
   (phones store photos rotated), then `convert("RGB")` (a transparent PNG is
   flattened on white, since JPEG has no transparency); save as JPEG, quality
   85. The orientation tag survives `thumbnail`, so the result is upright.
- **Worst-case memory:** PNG and WebP decode in full. At the 50 MP cap an RGBA
  image is about 200 MB, held briefly by one worker. Accepted, with three
  workers; the cap is what bounds it (A.8.6).
4. If Pillow can't read the image (`OSError`, `ValueError`, `SyntaxError`, which
   includes `UnidentifiedImageError`), return `None`, logged at WARNING by the
   route with the node id and the original name. The upload is still accepted,
   with `has_thumb = 0`; the grid then shows the full image scaled down.
- **When:** the thumbnail is made **before** the transaction (§ 5.6 step 2), so
  Pillow never runs while the node row is locked.
- **The original** is stored exactly as uploaded (see § 10.2 on EXIF). The
  thumbnail has no EXIF.

### 5.4 Title and names

- **Title:** required; control characters (`\x00`–`\x1f`, `\x7f`) removed;
  trimmed; 1–200 characters. The upload dialog pre-fills it from the file name
  without its extension.
- **`original_name`:** the client's name, cut to the part after the last `/` or
  `\`, control characters removed, truncated to 255; empty → the title. Display
  only (Vue escapes it).
- **Download name:** `<title>.<ext>`, built by `send_file(download_name=…)`,
  which already writes both an ASCII `filename` and an RFC 5987 `filename*` for
  the full title. `safe_download_name` only drops path separators, quotes and
  control characters.
- `kind` and `title` come from `request.form` (multipart), so the route calls
  `validate_document` directly rather than `clean_body` (which reads JSON).

### 5.5 Remove

- One statement, so two removes at once give one 204 and one 404:
  `UPDATE equipment_documents SET removed_at = NOW(), removed_by = %s WHERE id = %s AND equipment_id = %s AND removed_at IS NULL`;
  `rowcount == 0` → 404.
- Before it, in the same transaction: lock the node (`LOCK_EQUIPMENT`, lock (1))
  and refuse a scrapped node from that locked row (409), as S002 requires.
- The row and the file stay (ISO 55001 control). Removed documents are hidden
  from the list and their files are no longer served (404).
- Scrapped equipment: no uploads and no removals (409); its documents stay
  viewable.

### 5.6 Writing safely

Order on upload. The slow part, writing to the NFS share, happens **outside**
the node lock, so a hanging mount never blocks other writes to that node (BR2-04,
which corrects round 1's ordering):
1. Permission; load the node with access (404); the size check before parsing
   (§ 5.2).
2. Validate kind and title (400); read the file up to the limit (400); detect
   its type (400); for a photo, make the thumbnail (§ 5.3; a pixel-cap 400
   here). **Early scrapped check** from the plain read of step 1 (409), so a
   scrapped node doesn't get files written at all.
3. **Write the files**, no transaction open: create the node's folder
   (`exist_ok`); write the file to a temporary name **in that folder** and
   `os.replace` it into place (all-or-nothing, also on NFS, because it stays
   within one folder); write the thumbnail the same way. On an `OSError`:
   remove what was written, then answer 503 "File storage is unavailable — try
   again later", logged at ERROR with the path and the errno (e.g. an expired
   Kerberos ticket on the App-FS mount).
4. **A short transaction:** lock the node row (`LOCK_EQUIPMENT`, the start of the
   global lock order), refuse a scrapped node **from that locked row** (409; the
   decision that counts, S002 BR3-01), insert the row, commit.
5. If step 4 fails for any reason (409, a database error): remove the files of
   step 3, then re-raise. A database error stays a logged 500.
- **Clean-up never hides the real error:** each removal is wrapped on its own;
  a failed removal is logged at WARNING and the original error is what the user
  gets.
- A file is never written in place, so a half-written file is never served.
- A crash between step 3 and the commit can leave an orphan file with no row.
  It is harmless (never served) and accepted; no clean-up job.
- `stored_name` = 32 random hex characters (`secrets.token_hex(16)`) + `.pdf` /
  `.jpg` / `.png` / `.webp`; the thumbnail is `<stored_name>.thumb.jpg`. The
  folder is the node id. Nothing from the client reaches a path.
- **Locks:** `documents.py` takes lock (1) only, briefly, and then touches
  `equipment_documents` rows, which nothing else locks, so no lock cycle is
  added. No file I/O happens while it holds the lock.

### 5.7 The upload limit setting

- Key `upload_max_mb` in `app_settings`, seeded 20 by the migration.
- Read at request time through `get_setting_int(cur, "upload_max_mb", 20, 1, 100)`,
  so a change applies at once, without a restart.
- Changed on the Settings page by IT admin (`settings:edit`): a JSON integer
  1–100, else 400. The 100 sits just under Flask's and Nginx's 101 MB ceilings
  (§ 5.2). Each change is logged at INFO with who, old and new value.

## 6. Storage

### 6.1 Where files live

- `DATA_DIR/equipment/<node_id>/<stored_name>` (and `<stored_name>.thumb.jpg`).
- `DATA_DIR` comes from the env var `DATA_DIR`; default `<repo>/data` in dev;
  a temporary folder in tests; `/app/data` in the container.
- One deployment is one organisation (`vel_yantra_master`), so there is no
  tenant level in the path. `DATA_DIR` must be one filesystem (no mount inside
  it), so `os.replace` stays atomic.

### 6.2 Serving

- `GET …/documents/<doc_id>/file` and `…/thumb` stream the file through Flask
  (`send_file`, `conditional=True`: ETag and 304) after the access check, with:
  - `Content-Type` from the row;
  - `Content-Disposition: inline` with the download name of § 5.4;
  - `X-Content-Type-Options: nosniff`;
  - `Cache-Control: private, max-age=3600`. Werkzeug's `send_file` marks a
    `max_age` response `public`; the route sets it to `private` afterwards.
- A row whose file is missing on disk → 404 "File missing", logged at ERROR (a
  sign the mount or the backup is wrong).

### 6.3 Showing files in the browser

The app sends its Keycloak token in an `Authorization` header (`api.js`), which an
`<img src>` or a plain link can't do. So the frontend **fetches files as blobs**
with the token (`apiGetBlob`) and shows them through `URL.createObjectURL`. One
auth mechanism; no tokens in URLs. Rules:
- **Thumbnails and the large photo:** object URLs in `<img>`.
- **Open a PDF:** the click handler opens the tab **synchronously first**
  (`const tab = window.open("", "_blank")`), then fetches the blob, then sets
  `tab.location = objectUrl`; on an error it closes the tab and shows the
  message. Opening the tab after the `await` would be blocked as a pop-up by
  Safari and, for slow downloads, by Chrome. If `window.open` returns `null`
  (some in-app browsers, e.g. inside WhatsApp), it falls back to Download.
- **Download a PDF:** an `<a :href="objectUrl" :download="title + '.pdf'">`,
  fetched on click, so a saved file is named `<title>.pdf` (a blob URL has no
  name of its own; Android would otherwise save a nameless file).
- **Revoking:** image object URLs are revoked when the list reloads, when the
  page follows a new `:id` (the component is reused, S003 BR2-02) and on
  unmount, so a long session doesn't keep every image in memory. **PDF** object
  URLs are revoked only on unmount, because the new tab may still be loading
  one when the list reloads.
- **Consequence, accepted:** the opened tab's address is a `blob:` URL; it can't
  be bookmarked or sent to a colleague. Links to a document come with QR (S007)
  or later.
- **The file input:** `<input type="file" accept="image/jpeg,image/png,image/webp">`
  for photos (`application/pdf` for documents), **without** `capture`: a phone
  then offers the camera **and** the gallery.

### 6.4 Deployment (in place; one item for the user)

Checked in `smtw_erp_devops` (15-10-2026):
- `erp_server/yantra/deploy.yaml` runs `app-fs/client/app-fs_setup.yaml`: keytabs,
  `rpc-gssd`, Kerberos tickets renewed every 6 h, the `/etc/fstab` mount of
  `/app-fs/Vel-Yantra-Master`.
- `compose.yml.j2` bind-mounts it as `/app/data` into **backend** and **worker**
  and sets `DATA_DIR: /app/data`.
- App-FS exports it to customer7 with `rw,all_squash,anonuid=1000,anongid=1000,sec=krb5`;
  the export root is `kla:kla 0775`. Every write lands as uid 1000.
- App-FS has its own backup (user).
- **Container user (done by the devops team, 15-10-2026):** `compose.yml.j2`
  now runs backend and worker as `user: "1000:1000"`, like weighbridge and Geo,
  so they use the renewed Kerberos user ticket rather than the machine
  credentials root would use.
  - **Consequence to check:** `deploy.yaml` writes `secrets_app.py` with mode
    `0600`, owned by `base_username`. uid 1000 can read it only if
    `base_username` **is** uid 1000 (`id <base_username>` on customer7). If not,
    the backend can't start, crash-loops, and the playbook's `/api/version`
    check fails. The devops team confirms this, or makes the file group-readable
    for gid 1000.
  - Nothing in the image needs root: `/app` is only read (hence
    `PYTHONDONTWRITEBYTECODE`, § 3), and the only writes go to `/app/data`.
  - After the next deploy, on the VM:
    `docker compose exec backend sh -c 'touch /app/data/.w && rm /app/data/.w && echo ok'`.

## 7. Design decisions

| Decision | Reason | Rejected alternative |
|---|---|---|
| Files on the App-FS share mounted at `/app/data` | Plan § 1 (decided); App-FS has its own backup | MinIO (Plan § 1: no) |
| Type detected from the first bytes | A renamed `.exe` isn't a PDF (ISO 27001 A.8.28) | Trusting the extension or the browser's content type |
| PDF + JPEG/PNG/WebP only | Covers manuals, drawings and phone photos; all display in a browser | Office files, DWG, HEIC |
| Thumbnails with Pillow, made before the transaction, pixel cap 50 MP | Phone photos are 3–8 MB; the cap protects memory (A.8.6); no decoding under a lock | No thumbnails; a global Pillow knob |
| Remove hides, never deletes | ISO 55001 controlled information | Hard delete |
| Blob fetch with the token; tab opened synchronously; `download` attribute | One auth mechanism; works on iPhone and Android | Signed URLs (a second auth path, tokens in logs) |
| The size limit in `app_settings`, edited on the Settings page | Configurable at runtime (base pattern), by IT admin, without SQL | A constant; a database-only value |
| Upload and remove need `equipment:edit` | The same people who maintain the register | Operators adding photos (§ 10.5) |
| Documents on any node level | A motor's datasheet belongs to the motor | Equipment level only |
| A separate blueprint `documents.py`; equipment's load and lock made public | `equipment.py` stays about the tree; no private names imported across modules | Adding to `equipment.py` |
| Remove as one conditional `UPDATE` | Two removes at once: one 204, one 404 | Locking the document row |
| A storage `OSError` → 503 | The user learns it's temporary; the log says why | A 500 |
| Files written before the short locking transaction | A hanging NFS mount never holds the node lock (BR2-04) | Writing inside the transaction |
| Ceilings at 101 MB, setting up to 100 | A file at the setting's maximum still fits with the multipart overhead | Ceilings at 100 MB |

## 8. API

Under `/api/equipment/<node_id>/documents` (collection routes with
`strict_slashes=False`, as `equipment_bp`):

| Method and path | Permission | Result |
|---|---|---|
| `GET /` | `equipment:read` | `{items, upload_max_mb}` (no `total`: one node's documents aren't paged); items not removed, `ORDER BY created_at DESC, id DESC`: `id, kind, title, original_name, content_type, size_bytes, has_thumb, created_at, created_by` |
| `POST /` (multipart: `kind`, `title`, `file`) | `equipment:edit` | 201, the new item |
| `GET /<doc_id>/file` | `equipment:read` | the file |
| `GET /<doc_id>/thumb` | `equipment:read` | the thumbnail; 404 when `has_thumb = 0` |
| `DELETE /<doc_id>` | `equipment:edit` | 204 (§ 5.5) |

- A `doc_id` that belongs to another node, or is removed → 404.
- The equipment page loads the list separately from the node.

Under `/api/settings`:

| Method and path | Permission | Result |
|---|---|---|
| `GET /app` | `settings:read` | `{upload_max_mb}` |
| `PUT /app` `{upload_max_mb}` | `settings:edit` | 200 `{upload_max_mb}`; 400 field `upload_max_mb` outside 1–100 |

## 9. Tests and acceptance

### Pure (`test_documents_core.py`)
- `detect_file_type`: real first bytes of PDF, JPEG, PNG, WebP; a text file, an
  `.exe` header, a HEIC header, empty input → `None`.
- `kind_accepts`: a PDF as a photo and a JPEG as a document are refused.
- `validate_document`: kind; title blank, 201 characters, control characters
  removed.
- `clean_original_name`: a Windows path, a Unix path, 300 characters, empty.
- `stored_name` format; `safe_download_name` (quotes, slashes, `\r\n`,
  non-ASCII).
- `make_thumbnail`: a small EXIF-rotated JPEG gives an upright thumbnail; an
  RGBA PNG gives a thumbnail; a header claiming 8 000 × 8 000 px (64 MP) is
  refused by the 50 MP cap; a truncated JPEG gives `None`.

### API (`test_documents_api.py`)
- Upload a PDF and a JPEG → 201; listed newest first with `upload_max_mb`; open
  returns the bytes, `Content-Type`, `nosniff`, `Cache-Control: private`; the
  JPEG's thumbnail exists.
- Wrong type, a type the kind refuses, too large (limit set to 1 in
  `app_settings`; both the `content_length` check and the read check), empty, no
  file, missing title → 400 with field.
- A corrupt JPEG body with a JPEG header → 201 with `has_thumb = 0`.
- An image header over 50 MP (e.g. 8 000 × 8 000) → 400 from the cap, not from
  Pillow's own limit.
- The 413 backstop: `MAX_CONTENT_LENGTH` lowered for the test **below**
  `upload_max_mb` + 64 KB, so the request passes check 2 and reaches it → 413
  with JSON `{error, field}`.
- No `Content-Length` (a chunked request in the test client) → still refused
  above the limit by check 3.
- Access: another unit's node → 404 for list, open, upload; operator upload →
  403; a `doc_id` of another node → 404.
- Scrapped node: upload and remove → 409; list and open → 200.
- Remove → 204, gone from the list, the file still on disk, `removed_by` set;
  a second remove → 404; open after remove → 404.
- Insert failure (monkeypatched) → no file left in the folder; a storage
  `OSError` (monkeypatched) → 503, nothing left behind.
- A row whose file was deleted from disk → 404 on open.

### Settings API
- `GET /api/settings/app`: manager and IT admin 200, operator 403.
- `PUT`: IT admin 200 and an INFO log line; manager 403; `0`, `101`, `"20"`,
  `20.5`, `true` → 400.
- `get_setting_int`: missing key, `abc`, `500` → the default, with a warning.

### Frontend (vitest)
- `formatBytes`: 0, 999, 1 536, 20 MB.

### Manual checks (user)
- On `RPP001`: upload a PDF manual and two phone photos (one taken in portrait);
  the thumbnails are upright; view the photos large with next/previous.
- **On an Android phone and on an iPhone:** "Add photo" offers camera and
  gallery; Open shows the PDF in a new tab; Download saves `<title>.pdf`.
- Upload a `.docx` renamed to `.pdf`: refused. A photo above the limit: refused
  in the dialog before sending.
- Remove a photo; it disappears; the equipment's history is unchanged.
- As operator: sees and opens documents, no upload or remove buttons.
- Settings → Uploads: IT admin changes the limit to 5; a 6 MB photo is refused.
- Restart the backend: files are still there (dev `data/` folder).
- After the next deploy: the write test of § 6.4 on the VM, and an upload on
  production.
- Settings → Uploads: set 100; a file just under 100 MB uploads (the 101 MB
  ceilings let it through).

### Acceptance
- `tooling/run-tests.bat` green; `npx vite build` clean.
- An engineer can attach the manual and nameplate photo of a machine and open
  them on an Android phone and an iPhone.

## 10. Open questions and assumptions

1. **Done (devops team, 15-10-2026) — container user** `1000:1000`. Open only:
   the `secrets_app.py` ownership check of § 6.4.
2. **For the user — EXIF (GPS position) in photos.** Keep originals as uploaded
   (the position is the plant; viewers are staff), or strip EXIF on upload
   (re-saving the photo: slightly lower quality, nothing a technician needs is
   lost)? Recommended: keep, for now.
3. **For the user — no malware scan** of uploads (ISO 27001 A.8.7). Accepted
   because files come from staff and only browsers open them? Recommended:
   accept.
4. **Assumption:** titles aren't editable after upload (remove and upload again).
5. **Assumption:** only `equipment:edit` uploads. Operators could add photos too;
   that fits TPM's autonomous maintenance but needs a new permission. Revisit with
   CIL in phase 4.

## 11. Amendments

(none)

## Review log

### Round 1 — `2-brief-review-r1.md` (Fable), answered 15-10-2026

| Finding | Severity | Response |
|---|---|---|
| BR1-01 PDFs in a new tab on phones | major | **Accepted, option 1.** Synchronous `window.open`, `download` attribute, error path, revoking, blob URLs not shareable; Android and iPhone checks (§ 1, § 6.3, § 9). |
| BR1-02 Storage already decided; NFS consequences | major | **Accepted.** Plan § 1 restated; the devops stack checked (mount, bind, `all_squash` to uid 1000, App-FS backup); the root-vs-uid-1000 point put to the user (§ 6.4, § 10.1). |
| BR1-03 Pillow safety | major | **Accepted, option 1.** `make_thumbnail` in `documents_core`, `formats=`, 50 MP cap, exceptions, RGB, made before the transaction; pure tests (§ 3, § 5.3, § 9). |
| BR1-04 The Settings page doesn't edit settings | major | **Accepted, option 1.** `GET/PUT /api/settings/app`, `get_setting_int`, bounds 1–100, a Settings card (§ 3, § 5.7, § 8, § 9). |
| BR1-05 Size-limit plumbing | minor | **Accepted.** JSON 413 handler; `upload_max_mb` in the list and a dialog check; `content_length` before parsing; `read(limit + 1)` (§ 5.2, § 8). |
| BR1-06 Failure handling while writing | minor | **Accepted.** One `try` around folder, temp, replace, thumbnail, insert; clean-up of all three; storage `OSError` → 503 (§ 5.6). |
| BR1-07 Private helpers; lock note; atomic remove; unique key | minor | **Accepted.** Public `load_node_for_user`/`LOCK_EQUIPMENT`; docstring note; conditional `UPDATE`; `UNIQUE_KEY_ERRORS` entry (§ 3, § 5.5, § 5.6). |
| BR1-08 `DATA_DIR` in the container and in tests | minor | **Accepted, adapted.** The env var is `DATA_DIR`, which production compose already sets; `ENV DATA_DIR` in the Dockerfile; set before `import config` in tests; `.dockerignore` (§ 3, § 6.1). |
| BR1-09 Header and name hygiene | minor | **Accepted.** Control characters removed; `send_file(download_name)`; `Cache-Control: private` set after `send_file`; `original_name` rule (§ 5.4, § 6.2). |
| BR1-10 EXIF, HEIC, file input | minor | **Accepted.** EXIF put to the user (§ 10.2); HEIC help line; `accept` without `capture` (§ 5.2, § 6.3). |
| BR1-11 Standards corrections | minor | **Accepted.** ISO 14224 Table 5 wording; ISO 55001 7.6.3; A.8.6, A.5.34, A.8.7; TPM steps 1–3; Pillow quarterly, no apt packages (§ 2, § 3). |
| BR1-12 Small omissions | nit | **Accepted.** `uv.lock`; form fields not `clean_body`; ordering; `saveLabel` "Upload"; placement below Notes; `strict_slashes`; `formatBytes` with a test (§ 3, § 5.4, § 8, § 9). |

### Round 2 — `2-brief-review-r2.md` (Fable), answered 15-10-2026

All twelve round-1 answers verified in the text.

| Finding | Severity | Response |
|---|---|---|
| BR2-01 The compose change is already made; `secrets_app.py` ownership | major | **Accepted.** § 6.4 and § 10.1 state that the devops team added `user: "1000:1000"`; the `0600`/`base_username` consequence and its check added; `PYTHONDONTWRITEBYTECODE` (§ 3). |
| BR2-02 `content_length` missing; ceiling headroom; 413 is a backstop | minor | **Accepted.** Missing length skips check 2; Flask and Nginx at 101 MB; the 413 test lowered below the setting (§ 3, § 5.2, § 9). |
| BR2-03 The pixel-cap test; thumbnail before transpose; memory | minor | **Accepted.** 8 000 × 8 000 test; `thumbnail` then `exif_transpose`; 200 MB worst case stated (§ 5.3, § 9). |
| BR2-04 NFS writes under the node lock | minor | **Accepted.** Early scrapped check, files written first, short locking transaction, clean-up that never masks the error, path and errno logged (§ 5.6, § 7). |
| BR2-05 `window.open` null; PDF URL revoking | minor | **Accepted.** Fallback to Download; PDF URLs revoked on unmount only (§ 6.3). |
| BR2-06 Integer rule; who changed the limit; where the helper lives | minor | **Accepted.** JSON integer only; INFO log with actor, old and new; `settings.py` (§ 3, § 5.7). No `updated_by` column. |
| BR2-07 Small points | nit | **Accepted.** Temp folder clean-up; 413 message from the constant; `test_settings_api.py`; no `total`; `PYTHONDONTWRITEBYTECODE`; A.8.10 note (§ 2, § 3, § 8). |
