```
Step: S006 — Documents and photos on equipment
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 15-10-2026
```

# S006 — Brief review, round 1

**Verdict: four `major` findings are open (BR1-01 to BR1-04); no `blocker`.**
The shape of the step is right and proportionate. The majors are all cheap to
fix in the brief: one behaviour the acceptance test depends on but the brief
leaves to the browser (PDF in a new tab from a blob URL), one Plan.MD decision
the brief re-asks instead of applying (NFS storage), one safety gap the coder
would otherwise settle alone (Pillow and oversized images), and one open
question that the current code already answers (the Settings page).

Reviewed against the working tree: `backend/equipment.py` (S005 state),
`local_db.py` v1–v5, `config.py`, `app.py`, `api_common.py`, `db_helpers.py`,
`auth_utils.py`, `config_rbac.py`, `settings.py`, `tests/conftest.py`,
`tests/test_rbac.py`, `tests/test_modules.py`, `tests/test_equipment_api.py`;
`frontend/src/api.js`, `stores/auth.js`, `views/EquipmentDetailView.vue`,
`components/FormModal.vue`, `views/SettingsView.vue`, `vite.config.js`;
`tooling/build/Dockerfile.backend`, `nginx.conf`, `gunicorn.conf.py`,
`.dockerignore`, `.gitignore`, `backend/pyproject.toml` + `uv.lock`
(Flask 3.1.3, Werkzeug 3.1.9); `docs/Plan.MD`, `Maintenance-Philosophy.md`,
`Plant-Facts.md`, S002 brief § 6, S003 brief § 4.2, `SMTW-WebApp-Base.md`
§ File Upload / Object Storage / Business Settings, CLAUDE-COMMON.

---

## Major

### BR1-01 — major — "A PDF opened in a new tab from its object URL" does not work reliably on phones, and the brief's acceptance depends on it

**Problem.** § 6.3 says a PDF is "opened in a new tab from its object URL", and
§ 9 accepts the step when "an engineer can attach the manual … and open [it] on
a phone". The brief does not say *how* the tab is opened, and the obvious code
(`await apiGetBlob(...)` then `window.open(url)`) behaves differently per
browser:

- **Pop-up blocking.** `window.open` after an `await` is no longer inside the
  click's user activation. Safari (desktop and iOS) blocks it outright; Chrome
  allows it only while its ~5 s "transient activation" lasts, so a 10 MB manual
  on mobile data is blocked and a 200 kB one is not. Nothing in the brief tells
  the coder to open the window synchronously.
- **File name.** A blob URL has no name. "Save as" from the new tab, and any
  browser that downloads PDFs rather than showing them (Android Chrome on many
  versions), produces a file named like `a1b2c3d4-…` with **no extension**, so
  the phone may not know which app opens it. The `Content-Disposition`
  filename the backend carefully sets (§ 6.2) never reaches the browser's
  download logic, because the file arrives via `fetch`.
- **No shareable link.** The tab's address is `blob:https://…/uuid`; it cannot
  be copied to a colleague or bookmarked. Acceptable for v1, but it should be a
  stated consequence, not a surprise.

**Why it matters.** Shop-floor users are phone-first (Plan § 1, Plant-Facts
§ 5). If the manual "opens" only on desktop Chrome, the step fails its own
acceptance line and the manual check "open the PDF in a new tab" on a phone.

**Options.**
1. **Keep blob fetching (one auth mechanism) and specify the mechanics.**
   Open the window *synchronously* in the click handler
   (`const tab = window.open("", "_blank")`), fetch the blob, then set
   `tab.location = objectUrl` (and close the tab on error). For naming, render
   the document row as `<a :href="objectUrl" :download="title + '.pdf'">` once
   the blob is fetched, so "Save" and Android downloads get `<title>.pdf`.
   State that the tab's address is a blob URL and links aren't shareable in v1.
2. **Short-lived signed link** (`POST …/documents/<id>/link` → one-time token,
   60 s) so a plain `<a href target="_blank">` and `<img src>` work everywhere
   with the server's `Content-Disposition`. The brief rejected this as a second
   auth path; the cost is real (tokens in URLs land in logs and history), so
   only if option 1 proves too fiddly in the manual checks.
3. Always download (`<a download>`), never a new tab. Simple, but annoying on
   desktop.

**Recommendation:** option 1, written into § 6.3 as rules the coder follows
(synchronous open, `download` attribute with `<title>.pdf`, error path), plus a
manual check on an Android phone and an iPhone, not only "a phone". Add to
§ 6.3 as well: object URLs are revoked when the list is reloaded or the page
follows a new `:id` (the component is reused, S003 BR2-02), not only on
unmount — otherwise a long browsing session leaks every thumbnail ever shown.

### BR1-02 — major — Storage is already decided in Plan.MD (App-FS NFS export, no MinIO); the brief re-asks it and the deployment note misses what NFS implies

**Problem.** Plan.MD § 1, row *Files*: "Photos and documents on disk under
`data/`, which is an **App-FS NFS export mounted into the container** (like
OneERP's files). **No MinIO**." The brief's § 10.1 asks the user "Server disk,
or MinIO if it already runs?", § 7 lists MinIO as an alternative "if it already
runs", and § 6.4 asks for "a persistent volume at `/app/data`" with no mention
of NFS.

**Why it matters.** Re-asking a decided question costs the user a decision he
has made, and the NFS detail has consequences the coder and the user must know:

- **Writes as root.** `python:3.12-slim` runs gunicorn as root. An NFS export
  with `root_squash` (the default) maps root to `nobody`, and every upload
  fails with `EACCES` on the first production try. OneERP works because Frappe
  runs as its own user. The deployment note must say which uid the backend
  writes as, and that the export's ownership/squash settings must match (or
  the container runs as a dedicated uid).
- **Atomic rename.** § 5.6's temp-name-then-rename is atomic on NFS too, but
  only within one directory on the same export; the brief should say the temp
  file is written *in the target folder* (it does: "in the target folder") —
  keep it, and add that `DATA_DIR` must not straddle a mount boundary.
- **Backup.** ISO 27001 A.8.13 is then met by App-FS's own backup regime, not
  by "the server backup must include that volume". Say which.

**Options.**
1. Drop § 10.1; restate the Plan decision in § 6.1/§ 6.4 (NFS export mounted
   at `/app/data`); add the uid/root_squash check to § 6.4's user actions;
   remove MinIO from § 7's rejected column or mark it "Plan § 1: no".
2. Keep § 10.1 if the user wants to revisit the Plan — then say so explicitly
   ("Plan § 1 says NFS; confirm it still stands").

**Recommendation:** option 1. Nothing in the code changes; only the brief's
text and the user's deployment checklist.

### BR1-03 — major — Pillow: no pixel cap, no exception policy, no restriction of decoders, no RGBA handling; the coder would decide each alone

**Problem.** § 5.3 says "if Pillow can't read the image … accepted with
`has_thumb = 0`" and nothing else. Four things are left open:

1. **Decompression bombs / memory.** A 20 MB PNG or WebP can decode to hundreds
   of megapixels (Pillow's default `MAX_IMAGE_PIXELS` is ~89 MP; it only *warns*
   above that and raises `DecompressionBombError` above ~179 MP, which is
   ~540 MB of RGB). With three sync gunicorn workers and 100 MB of request
   ceiling, two such uploads can take the backend down. JPEG is safer
   (`Image.thumbnail()` uses draft/DCT scaling), PNG and WebP are not. Note the
   original is also *served* as-is, so a 150 MP photo would also crash the
   phone that views it — refusing is right, not "accept without thumbnail".
2. **Which exceptions mean "can't read".** Pillow raises
   `UnidentifiedImageError`, `OSError` (truncated), `SyntaxError` (broken PNG
   chunks), `ValueError`, and `DecompressionBombError`. CLAUDE-COMMON forbids
   silently swallowing; the brief must say what is caught, that it is logged
   at WARNING with the doc id, and that a bomb is a 400, not a `has_thumb = 0`.
3. **Decoder restriction.** `Image.open(data, formats=["JPEG", "PNG", "WEBP"])`
   makes sure a file whose first bytes say JPEG cannot reach any other Pillow
   decoder — cheap hardening that fits the A.8.28 line in § 2.
4. **PNG with transparency.** JPEG cannot hold alpha; saving an RGBA or
   palette image as JPEG raises `OSError: cannot write mode RGBA as JPEG`.
   Without `convert("RGB")` (flatten on white) every transparent PNG — common
   for drawings and logos — silently ends up `has_thumb = 0`.

Also unplaced: **where** the thumbnail code lives and **when** it runs. § 3
puts detection in `documents_core.py` and I/O in `file_store.py`; the
thumbnail is neither. § 5.6 step 3 writes it inside the transaction while the
node row is locked, which means Pillow decodes under the lock.

**Why it matters.** Memory exhaustion is the one way this step can hurt the
whole app, and it is reachable by anyone with `equipment:edit`. ISO 27001
A.8.28 (secure coding) and A.8.6 (capacity management — "resources shall be
monitored and adjusted in line with current and expected requirements") both
apply.

**Options.**
1. Add to § 5.3: `make_thumbnail(data, max_side=400) -> bytes | None` in
   `documents_core.py` (bytes in, bytes out; Pillow is a library, not a
   framework, so this stays a pure function); open with `formats=`; read the
   header first and refuse above a cap — e.g. 50 MP → 400 field `file`
   "Photo too large (N megapixels)" (today's phones output 12 MP by default,
   48 MP at most); `exif_transpose`; `convert("RGB")`; `thumbnail((400, 400))`;
   JPEG quality ~85; catch `(OSError, ValueError, SyntaxError)` → `None` with
   a logged warning; let `DecompressionBombError` become a 400 as a backstop.
   Generate in § 5.6 step 2 (before the transaction), write in step 3.
2. Lower `Image.MAX_IMAGE_PIXELS` globally instead of the header check.
   Simpler, but a global knob for a one-route concern.

**Recommendation:** option 1, with the pure tests in § 9 extended: a tiny
EXIF-rotated JPEG (upright thumbnail), an RGBA PNG (thumbnail produced), a
header claiming 20 000 × 20 000 px (refused), a truncated JPEG (`None`).

### BR1-04 — major — § 10.4 is decidable now: the Settings page does not edit settings; the setting's read, parse and bounds are unspecified

**Problem.** § 3 and § 10.4 leave it to the coder: add a Settings-page field
"if the Settings page already edits app settings; otherwise … the screen comes
later (the coder reports which)". I checked: `settings.py` has one route,
`GET /db-status`; `SettingsView.vue` shows one card, Database status. There is
no `app_settings` read or write anywhere in the backend. So the condition is
known and the brief should decide, not defer to the coder (CLAUDE-COMMON
"decisions taken mid-flight get surfaced"; README gate 2 "anything the brief
doesn't cover is raised with the user, not decided in code").

Three things are then undefined either way:
- **Where the read helper lives.** A `get_setting(cur, key, default)` is the
  first `app_settings` reader in the codebase; it belongs in `settings.py` (or
  `db_helpers.py`), and later steps (escalation times, Plan Q2) will reuse it.
- **Parsing and bounds.** `setting_value` is `TEXT`. What if it holds `abc`,
  `0`, `-5` or `500`? The Flask ceiling is 100 MB (§ 5.2), so a value above 100
  can never be reached and would silently produce HTML 413s. Rule needed:
  integer 1–100; otherwise fall back to 20 and log a warning (an admin typo
  must not break every upload).
- **Scope of the step.** A minimal `GET/PUT /api/settings/app` (keys
  whitelisted in code, `settings:read` / `settings:edit` already exist in
  `config_rbac.py`) plus a small card on `SettingsView.vue` is perhaps 60
  lines and two tests; or it is deferred and IT admin runs an `UPDATE`.

**Options.**
1. **In scope:** `GET /api/settings/app` → `{upload_max_mb}`;
   `PUT /api/settings/app` (`settings:edit`) with the 1–100 rule; a card on
   the Settings page. Tests: operator 403, manager read-only 403 on PUT, bad
   value 400.
2. **Deferred to a settings step:** state it; the migration seeds 20; IT admin
   changes it in the DB; the read helper still goes in `settings.py` with the
   parse rule above.

**Recommendation:** option 1 — the base pattern says "configurable at runtime
(store in `app_settings` …)", and a setting nobody can reach without SQL is not
configurable at runtime. Either way, remove the conditional wording from § 3
and § 10.4.

---

## Minor

### BR1-05 — minor — Size-limit plumbing: 413 bodies are HTML, the frontend never learns the limit, and the upload is parsed in full before the check

**Problem.**
- Flask's `MAX_CONTENT_LENGTH` and nginx's `client_max_body_size` both answer
  **413 with an HTML page**, not `{error, field?}`. `api.js` falls back to
  `response.statusText` ("REQUEST ENTITY TOO LARGE"). Register
  `RequestEntityTooLarge` in `api_common.register_error_handlers` →
  `{"error": "The file is larger than 100 MB", "field": "file"}` (nginx's own
  413 stays HTML; it is reached only above 100 MB).
- The frontend has no way to know `upload_max_mb`, so a 20 MB photo on mobile
  data is sent in full and refused at the end. Return it with the list
  (`GET …/documents` → `{items, upload_max_mb}`) and check `file.size` in the
  dialog before sending ("Larger than N MB").
- Werkzeug parses the whole multipart body into a spooled temp file when
  `request.files` is first touched, so "read the file into memory up to the
  limit" happens after the 100 MB has already been received. Cheap gain: compare
  `request.content_length` with `upload_max_mb` (plus a small allowance for the
  other fields) **before** touching `request.files`; then read
  `file.read(limit + 1)` and refuse on `len > limit`. State the `+ 1`.

**Why it matters.** User-facing error text and wasted mobile data; the rest is
clarity for the coder. Memory per request stays ≤ `upload_max_mb` (the spool is
on disk), which is fine for three workers — worth stating as checked.

**Recommendation:** add the three points to § 5.2 and § 8.

### BR1-06 — minor — § 5.6 handles only an insert failure; disk errors, temp-file leftovers and the thumbnail write are not covered

**Problem.** Step 4 says "if the insert fails, delete the files just written".
Not said: what happens when the **file write or rename** fails (NFS hiccup,
disk full, `EACCES` from BR1-02), when the **thumbnail write** fails after the
original is in place, or when a temp file is left behind by a failed rename.

**Recommendation.** Rewrite step 3–4 as: generate the thumbnail bytes before
the transaction (BR1-03); inside the transaction, lock the node, then in one
`try`: `makedirs(exist_ok=True)`, write temp, `os.replace` into place, write
`.thumb.jpg`, insert the row; on **any** exception remove the temp file, the
final file and the thumbnail if they exist, and re-raise (an `OSError` stays a
logged 500 — the base rule in S002 § Errors). Also say `file_store` must never
write in place (so a half-written file is never served) — it already follows
from temp+rename; make it explicit.

### BR1-07 — minor — Cross-module use of private helpers; lock-order note; the remove must be an atomic UPDATE

**Problem.**
- `documents.py` is to "reuse `_load_node_for_user` and the node lock", but
  both `_load_node_for_user` and `_LOCK_EQUIPMENT` are module-private names in
  `equipment.py` (verified, lines 95 and 219). Importing underscored names
  across modules is the kind of thing the code reviewer will flag. Say: rename
  to `load_node_for_user` (public), or add a one-line public wrapper; the
  brief's "no change to the existing routes" still holds.
- `equipment.py`'s docstring states the global lock order for "every write in
  this module" and the interaction with `masters.py`. A second module now locks
  equipment rows. Add to § 5.6: documents.py takes lock (1) only and then
  touches `equipment_documents` rows, which nothing else locks — no cycle; and
  have the coder extend the docstring's interaction paragraph.
- **Remove:** two concurrent removes must give one 204 and one 404. Specify
  `UPDATE equipment_documents SET removed_at = NOW(), removed_by = %s WHERE id = %s
  AND equipment_id = %s AND removed_at IS NULL` and decide 404 from
  `cur.rowcount == 0`. No lock on the document row is needed; the node lock
  (1) is taken only for the scrapped decision from the locking read, as S002
  requires.
- `stored_name` collision is astronomically unlikely, but a 1062 on
  `uq_equipment_documents_stored` would currently map to the generic 409
  "Conflicts with an existing record; reload". Add it to `UNIQUE_KEY_ERRORS`
  with "Retry the upload", as `uq_equipment_code` does.

### BR1-08 — minor — `DATA_DIR`: nothing tells `config.py` it is in the container; tests need the env var before import

**Problem.** § 3 / § 6.1: default `<repo>/data` "in dev and test", `/app/data`
"in the container". `config.py` has no container signal; the version-file
trick (try two paths) does not transfer, because `/app/../data` is `/data`.
Also `file_store` must read `config.DATA_DIR` at call time (not bind it at
import) if a session fixture is to point it at a temp folder; and
`conftest.py` sets env vars *before* `import config` (line 14), which is the
natural place for `YANTRA_DATA_DIR`.

**Recommendation.** One rule: `DATA_DIR = os.environ.get("YANTRA_DATA_DIR") or
<repo>/data`; `Dockerfile.backend` gains `ENV YANTRA_DATA_DIR=/app/data`
(the coder's file; list it in § 3). Tests: `os.environ["YANTRA_DATA_DIR"] =
tempfile.mkdtemp(...)` next to `YANTRA_TESTING` in `conftest.py`. Add `data/`
to `.dockerignore` as well (it has `backend/uploads/` from the template, a path
this app does not use).

### BR1-09 — minor — Header and name hygiene: control characters, basename, truncation, and Werkzeug's `public` cache header

**Problem.**
- **Title in the header.** § 6.2 builds `Content-Disposition` from the title.
  Werkzeug refuses a header value containing `\r` or `\n` with a 500. The
  title rule (§ 5.4) does not exclude control characters, and
  `safe_download_name` (§ 9) lists quotes, slashes and non-ASCII only. Add:
  strip `\x00–\x1f` and `\x7f` (or refuse them at validation).
- **RFC 5987.** `send_file(download_name=…, as_attachment=False)` already
  emits `inline; filename=<ascii>; filename*=UTF-8''<quoted>` (Werkzeug 3.1
  `send_file`). Say the route uses that rather than hand-building the header;
  `safe_download_name` then only needs to drop path separators, quotes and
  control characters.
- **`Cache-Control`.** Werkzeug's `send_file` with `max_age > 0` sets
  `Cache-Control: public, max-age=…`. The brief wants `private`. The coder
  must set `response.cache_control.public = None` / `.private = True` after
  `send_file`, and the API test should assert `private`. (`conditional=True`,
  Flask's default, gives ETag/304 — worth keeping and stating.)
- **`original_name`.** Can be empty (some camera captures), can contain a
  path (old browsers send one), can exceed 255 characters. Rule: basename of
  both `/` and `\`, truncate to 255, empty → the title. Display only; Vue
  escapes it.

### BR1-10 — minor — EXIF/GPS: wrong cross-reference and an unsurfaced privacy decision; HEIC and the file input

**Problem.**
- § 5.3 says re-encoding "would also drop the phone's GPS location from EXIF
  … See § 10.2", but § 10.2 is about Excel/Word files. There is no open point
  about EXIF at all. Keeping originals untouched means every photo carries the
  photographer's phone location and time, visible to everyone with
  `equipment:read` via a download. That is a small, probably acceptable
  privacy decision (the location is the plant; viewers are staff) — but it is
  the user's to make: ISO 27001 **A.5.34 (privacy and protection of PII)**.
  Make it an explicit assumption in § 10, with the alternative "strip EXIF on
  upload (`exif_transpose` then re-save, losing nothing a technician needs)".
- **HEIC.** iPhones shoot HEIF by default. Safari transcodes to JPEG for
  `<input type="file">` uploads as long as `accept` does not include HEIC, so
  the camera path works; a HEIC shared from Files/WhatsApp still arrives as
  HEIC, fails magic-byte detection (`ftypheic` at offset 4) and gets the
  generic 400. Add a sentence to the message or dialog help: "iPhone HEIC
  photos: set Camera › Formats › Most Compatible, or share as JPEG". Pillow
  does not read HEIC without `pillow-heif`; not for this step — say so.
- **The file input.** "Add photo can open the camera" needs
  `<input type="file" accept="image/jpeg,image/png,image/webp">` **without**
  `capture`: with `capture="environment"` Android jumps straight to the camera
  and offers no gallery. Pin this in § 3/§ 9 so the manual check is
  deterministic.

### BR1-11 — minor — Standards: one claim overstated, one dependency fact wrong, and two things worth adding for the owner

**Problem and corrections (plain-language, as the project owner is learning):**

- **ISO 14224** — § 2 says the standard's "common equipment data includes the
  manufacturer's documentation". Not quite: ISO 14224:2016 Table 5 (equipment
  data) lists *manufacturer's data* — manufacturer name, model/type
  designation — and *design data* (capacity, power, …), plus free-text remarks.
  Manuals and drawings are the **sources** you read those values from. Suggested
  wording: "ISO 14224 Table 5 expects the manufacturer's name, model and design
  data on every equipment record; the manual and drawings are where those
  values come from, so keeping them with the record lets anyone verify or
  complete the fields later."
- **ISO 55001** — § 7.5 "Information requirements" and § 7.6 "Documented
  information" (7.6.3 is "control of documented information": available where
  needed, protected, with changes controlled) — correct. The 2024 revision
  keeps these clause numbers, so the "(2014 numbering)" caveat is harmless.
  What the clause asks of Yantra, in one line: know who added or removed a
  document and when, and never lose one silently — which § 5.5 gives.
- **ISO 27001:2022** — A.8.3, A.5.12, A.8.13, A.8.28 are the right controls.
  Add **A.8.6 Capacity management** for BR1-03 (memory) and **A.5.34** for
  BR1-10 (EXIF). Also state the assumption that uploads are **not scanned for
  malware** (A.8.7): the magic-byte check is type enforcement, not antivirus;
  accepted because files are only ever opened by browsers and come from staff.
  The user should know that is a deliberate gap.
- **TPM** — "step 1, initial cleaning" refers to JIPM's seven steps of
  autonomous maintenance. Photos of the *standard condition* belong to step 3
  ("cleaning and lubrication standards") and to **visual controls** generally;
  before/after photos are a step-1 practice. Say "steps 1–3 and visual
  controls" so the owner gets the right map.
- **Pillow** — § 3: "actively maintained (monthly releases)". Pillow releases
  **quarterly** (January, April, July, October) with patch releases between;
  current major is 12.x; Python 3.12 supported; the wheels bundle libjpeg,
  zlib and libwebp, so **no apt packages** are needed in `Dockerfile.backend`
  (its comment "add more here … e.g. for Pillow" would otherwise tempt the
  coder to add `libjpeg-dev`). Maintained, healthy, the standard choice —
  the conclusion stands; the fact should be right.

---

## Nit

### BR1-12 — nit — Small omissions the coder would otherwise guess

- `uv.lock` changes with `uv add pillow`; `Dockerfile.backend` uses
  `uv sync --frozen`, so the lock must be in the commit. List `uv.lock` in § 3.
- `clean_body()` reads JSON; the upload is multipart, so `kind` and `title`
  come from `request.form` and `validate_document` is called directly. Say so,
  and that a missing `file` part is 400 field `file` ("Choose a file").
- List order "newest first": `ORDER BY created_at DESC, id DESC` (two uploads
  in one second), as S002 does for events.
- `FormModal`'s button says "Save". For an upload dialog "Upload" reads
  better; either accept "Save" or add a `saveLabel` prop (two lines). Decide.
- Placement: `EquipmentDetailView.vue` has a Notes card below Details / Parts /
  History; say "below Notes" (or above it) so the layout is fixed.
- Both blueprints under `/api/equipment`: give the new one `strict_slashes=False`
  on its collection routes, as `equipment_bp` does, so `/documents` and
  `/documents/` behave alike.
- Sizes on screen: a `formatBytes()` helper in `utils/` (KB/MB with one
  decimal) — mention it so it is not inlined in two components.
- The S003 practice "no component tests" is fine; `formatBytes` and the
  `isOutdated`-style helpers are pure and could get a vitest file cheaply.

---

## Checked and found consistent

- **Permissions.** No new keys; `equipment:read` / `equipment:edit` as in
  `config_rbac.py` and Plan § 3; `test_rbac.test_role_matrix` is unaffected.
  `settings:read` / `settings:edit` already exist for BR1-04 option 1.
- **Unit access and scrapped rule.** Reusing `_load_node_for_user` gives the
  same 404 for "missing" and "not at your units" (S002 § 6); 409 for scrapped
  from the locking read; lock (1) is the start of the global order (verified
  in `equipment.py` lines 7–16, 95). Operators see documents (`equipment:read`
  is `('*',)`), matching Plan § 3 and § 10.5.
- **Migration v6.** `app_settings(setting_key, setting_value TEXT)` exists from
  v1; `INSERT IGNORE` and `CREATE TABLE IF NOT EXISTS` are each safe to run
  twice, as the v5 comment requires; audit columns match the v2 convention;
  `test_modules` compares against `LATEST_VERSION`, so v6 passes.
- **Nginx / Flask ceiling.** `client_max_body_size 100M` is set in the `/api/`
  location; a 100 MB `MAX_CONTENT_LENGTH` matches. Nginx buffers the request
  body (`proxy_request_buffering` default on), so a slow mobile upload does not
  hold a gunicorn sync worker up to its 120 s timeout. `nosniff` is already
  added by nginx for `/api/` in production; the explicit header covers dev.
- **Blob fetching and caching.** `Cache-Control: private, max-age=3600` is
  honoured by the browser cache for `fetch` with an `Authorization` header, so
  revisits of thumbnails are cheap. `api.js` returns `null` for 204, so
  `apiDelete` works unchanged for the remove.
- **Test fixtures.** `_TABLES` with `FOREIGN_KEY_CHECKS = 0` tolerates any
  order; adding `equipment_documents` is enough. The monkeypatched-failure
  pattern (`test_a_failure_after_the_counter_bump_rolls_it_back`) transfers
  directly to "insert failure → no file left".
- **Plan § 5 / § 4.1.** `equipment_documents` is listed; tickets and jobs get a
  separate `attachments` table — the brief's "they'll reuse this storage"
  (file_store, not the table) is consistent.
- **No history event on upload/remove** matches S004's decision that notes are
  not in the history; traceability comes from the row's audit columns, which is
  what ISO 55001 § 7.6.3 asks.
- **Out-of-scope list** (QR labels S007, versioning, class-level documents,
  in-browser editing) matches Plan phase 2 and is proportionate.
- **Rejected SVG, Office and DWG** — right: SVG is an XSS vector when served
  inline; Office/DWG need other software and would need real malware scanning.
