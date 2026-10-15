```
Step: S006 — Documents and photos on equipment
Doc: brief-review r2
Author: Brief reviewer (Fable)
Date: 15-10-2026
```

# S006 — Brief review, round 2

**Verdict: one `major` finding is open (BR2-01); no `blocker`.** Every round-1
finding marked `Accepted` is reflected in the brief text, not only in the
Review log (checked item by item; list at the end). The rewrite is sound; the
remaining points are one fact about production that the brief states as it was
and not as it is, and a handful of edge rules in the new § 5.2, § 5.3, § 5.6
and § 6.3 that the coder would otherwise settle alone.

Reviewed against the working tree (S005 uncommitted): `backend/equipment.py`
(`_load_node_for_user` line 219, `_LOCK_EQUIPMENT` line 95), `local_db.py`
(v1 `app_settings`, v5, `LATEST_VERSION`), `db_helpers.py` (`transaction`,
`insert_row`), `api_common.py`, `app.py`, `config.py`, `settings.py`,
`config_rbac.py`, `tests/conftest.py`, `test_rbac.py`, `test_modules.py`,
`test_equipment_api.py` (the monkeypatch rollback pattern), `equipment_core.py`
/ `masters_core.py` (integer validation style); `frontend/src/api.js`,
`stores/navigation.js`, `router/index.js`, `views/SettingsView.vue`,
`components/FormModal.vue`, `views/EquipmentDetailView.vue`, `vite.config.js`;
`tooling/build/Dockerfile.backend`, `nginx.conf`, `gunicorn.conf.py`,
`.dockerignore`, `.gitignore`, `backend/pyproject.toml`, `uv.lock` (Flask 3.1.3,
Werkzeug 3.1.9 — and the installed Werkzeug source for `send_file` and
`max_content_length`); `smtw_erp_devops/erp_server/yantra/compose.yml.j2`,
`deploy.yaml`, `app-fs/client/app-fs_setup.yaml` and `git status`/`git diff`
of that repo. Settings and secrets files were **not** read (guard hook); the
export options (`all_squash,anonuid=1000,sec=krb5`) are taken as the planner
stated them. Docs: `Plan.MD` § 1/§ 3/§ 5, `Maintenance-Philosophy.md`,
`Plant-Facts.md` § 5, S002 brief § 6, S003 brief § 4.2, `SMTW-WebApp-Base.md`
§ API Response Conventions / File Upload / Object Storage / Testing,
CLAUDE-COMMON, CLAUDE.md.

---

## Major

### BR2-01 — major — § 6.4 and § 10.1 describe the production compose as it is in `HEAD`, but the `smtw_erp_devops` working tree already carries the `user: "1000:1000"` change, uncommitted

**Problem.** § 6.4 says "the Yantra containers run as **root** (no `USER` in
the image, no `user:` in compose). Recommended: add `user: "1000:1000"` to the
`x-backend` block", and § 10.1 asks the user to decide it. That is true of
`HEAD` (commit `32c75a7`, no `user:` line). But `git status` in
`smtw_erp_devops` shows two modified, uncommitted files:

```
 M erp_server/yantra/compose.yml.j2                               (+3: comment + user: "1000:1000")
 M erp_server/yantra/vars/example_settings_vel_yantra_master.yaml (2 lines; not read)
```

So the recommendation of § 10.1 already exists on disk in a repo the brief
lists as background, while the brief presents it as not yet done.

**Why it matters.**
- The user approves the brief believing nothing has changed in the devops
  repo; a change he has not been told about sits in its working tree.
  CLAUDE-COMMON: "never let a decision reach me for the first time as a fait
  accompli" and "nothing beyond the agreed scope". The planner's deliverable is
  `1-brief.md` only. (If the user made the edit himself during planning, this
  drops to a wording fix — but the brief still has to say what the working tree
  holds.)
- Running as uid 1000 has one consequence § 6.4 does not mention:
  `deploy.yaml` templates `secrets_app.py` with `mode: '0600'`, `owner:
  base_username`, and compose bind-mounts it read-only. As root the container
  could read it regardless; as uid 1000 it can read it **only if
  `base_username` is uid 1000**. The compose comment assumes that ("the uid
  that holds the cron-renewed user ticket (base_username)"), and the orchestrator
  reports weighbridge runs as 1000, so it is very probably right — but it is the
  check to make. A mismatch is loud, not silent: `config.py` raises on a missing
  `secrets_app`, the backend crash-loops, and the playbook's `/api/version`
  check fails. Also harmless but worth a line: `/app` is root-owned in the
  image, so Python cannot write `__pycache__` as uid 1000; it just does not
  cache bytecode.

**Options.**
1. The brief states the fact: "`user: "1000:1000"` is already prepared,
   uncommitted, in `smtw_erp_devops` (`compose.yml.j2`, plus a change to
   `vars/example_settings_vel_yantra_master.yaml`); the user reviews it and
   commits it with the S006 deploy, or reverts it." § 10.1 becomes "confirm
   (and commit)" rather than "add", and gains the check "`id <base_username>`
   on the VM is 1000" before the write test.
2. Revert the devops working-tree change so the brief's § 6.4 is true again,
   and keep § 10.1 as a pure question.

**Recommendation:** option 1 — the change is the right one; the brief only has
to be truthful about where it stands and name the uid check.

---

## Minor

### BR2-02 — minor — § 5.2 size checks: `content_length` can be `None`; the 100 MB ceilings have no headroom at the top of the range; the 413 is a backstop, not the normal path

**Problem.**
1. **`request.content_length` is `None`** when the body is chunked (no
   `Content-Length`). Browsers always send a length for `FormData`, so this is
   curl and scripts only, but the rule is missing: skip check 2 and rely on
   check 3 (`read(limit + 1)`) and Werkzeug's ceiling (which, from 3.1, is
   enforced on chunked streams too).
2. **Headroom at `upload_max_mb = 100`.** A file of exactly 100 MB passes the
   dialog (`file.size <= 100 MB`), but the multipart body is a few hundred bytes
   longer. Nginx's `client_max_body_size 100M` is exactly 104 857 600 bytes, so
   in production it answers an **HTML 413** before Flask; in dev Flask's 413
   says "larger than 100 MB" for a file that is at the allowed size. Only the
   top value is affected, but it is the value the brief promises works.
3. **Which check answers first.** I checked Werkzeug 3.1.9 (`wsgi.get_input_stream`):
   `max_content_length` is enforced when `request.files`/`stream` is first read,
   never before the route. So the route's check 2 runs first and answers 400 for
   anything with a `Content-Length`; the 413 JSON handler fires only for a
   chunked body, or in the headroom gap of point 2. The sentence "Above 100 MB,
   Flask's `MAX_CONTENT_LENGTH` answers 413" should say the route's 400 comes
   first and the handler is a backstop. The § 9 test "over 100 MB
   (`MAX_CONTENT_LENGTH` lowered) → 413" works only when the lowered ceiling is
   **below** `upload_max_mb` MB + 64 KB (e.g. ceiling 1 MB, setting 20, file
   2 MB) — state that, or the coder will write a test that gets 400.

The 64 KB allowance itself is fine: kind, a 200-character title and a
255-character file name in UTF-8 plus boundaries are under 3 KB.

**Options.**
1. Rules: `content_length is None` → skip check 2. Ceilings with headroom:
   `MAX_CONTENT_LENGTH = 101 MB`, nginx `client_max_body_size 101M`
   (`tooling/build/nginx.conf` joins § 3's file list); the 413 message derives
   from the constant.
2. Keep the ceilings and cap the setting at 99.

**Recommendation:** option 1; and reword the 413 sentence and the test as in
point 3.

### BR2-03 — minor — § 5.3 thumbnails: the 50 MP test exercises Pillow's bomb check rather than the cap; `exif_transpose` before `thumbnail` forces a full decode; the worst-case memory should be stated

**Problem.**
1. **The test does not test the cap.** `Image.open` itself runs Pillow's
   decompression-bomb check on the header size: above 2 × `MAX_IMAGE_PIXELS`
   (≈ 178.9 MP) it raises `DecompressionBombError`; between 89.5 and 178.9 MP
   it emits a `DecompressionBombWarning`. A 20 000 × 20 000 header (400 MP) is
   refused by Pillow before the brief's 50 MP rule runs, so the § 9 test
   "a header claiming 20 000 × 20 000 px is refused" proves the backstop, not
   the cap. Use e.g. 8 000 × 8 000 (64 MP) for the cap, and keep a 400 MP case
   for the backstop if wanted. (The warning for 89–179 MP is harmless — the cap
   refuses first — but it shows up in pytest output; silencing it with
   `warnings.simplefilter("ignore", Image.DecompressionBombWarning)` in
   `make_thumbnail` is one line, or leave it.)
2. **Order of operations.** § 5.3 step 3 does `exif_transpose` then
   `thumbnail`. `exif_transpose` decodes the full image and makes a transposed
   full-size copy: at the 50 MP cap that is 150 MB (RGB) twice. `thumbnail()`
   on a JPEG uses DCT scaling (`draft`) and never decodes at full size — but
   only if it runs **first**. The EXIF stays in `img.info` after `thumbnail()`,
   so `thumbnail((400, 400))` → `exif_transpose` → `convert("RGB")` gives the
   same upright result and keeps a phone JPEG at a few MB of memory.
3. **PNG and WebP cannot be draft-scaled.** A 50 MP RGBA PNG decodes to 200 MB
   in one worker; three workers in the worst case 600 MB, plus the spooled
   request body on disk. Phones produce JPEG, so a 50 MP PNG is an oddity, but
   the brief says "the cap protects memory" without the number. Either state
   it (and that the VM has the headroom) or give PNG/WebP a lower cap (25 MP).

**Why it matters.** ISO 27001 A.8.6 (capacity management) is the control the
brief cites for this; the figure is what makes the claim checkable.

**Recommendation:** fix the test size; swap the order to thumbnail-then-transpose;
state the worst-case figure and keep 50 MP unless the VM is tight.

### BR2-04 — minor — § 5.6: file I/O runs on the NFS share while the node row is locked; clean-up errors can mask the real error

**Problem.**
1. **I/O under the lock.** Step 3 takes lock (1) and then creates the folder,
   writes the file, renames it and writes the thumbnail — all on the App-FS
   mount — before the insert. A slow or hung NFS write (expired ticket; the
   mount is `hard` by default) holds the node lock for up to gunicorn's 120 s
   timeout, and every other write on that node waits behind it: edit, status
   change, and "add part" (`_load_target_node` locks the parent). Round 1
   (BR1-06) asked for the writes inside the one `try`, which the brief did;
   it did not have to be inside the **transaction**, and that is my correction.
   An order that holds no lock during I/O: step 1 plain-reads the node (the
   row has `status`) → early 409 if scrapped; step 2 as now; step 3 writes
   the file (temp + `os.replace`) and the thumbnail; step 4 is one short
   transaction: lock (1), scrapped from the locked row (409), insert. Any
   failure from step 3 on deletes the three files and re-raises. The cost is
   a node scrapped between step 1 and step 4: the files are written and deleted
   once — rare and harmless. The ISO 55001 traceability is unchanged (row and
   file still land together or not at all).
2. **Clean-up that fails.** The `except` branch deletes the temp, final and
   thumbnail files — on the storage that just failed. If a delete raises, the
   original `OSError` is replaced by the clean-up's, and the 503 becomes a 500
   with the wrong cause. Rule: each delete is wrapped (`contextlib.suppress
   (OSError)` or a logged try), then the original exception is re-raised.
3. **The 503 text for a permanent fault.** `PermissionError` (the uid mismatch
   of § 6.4) and `ENOSPC` are `OSError` too; "File storage is unavailable — try
   again later" is right for a ticket hiccup and misleading for those. Fine as
   long as the ERROR log line carries the path and the errno so IT admin sees
   the real cause — say so.

**Recommendation:** adopt the order in point 1 (or state why the lock must
cover the I/O), add the clean-up rule, and the log content.

### BR2-05 — minor — § 6.3: `window.open` can return `null`, and the revoke rule races the new tab's navigation

**Problem.**
1. `window.open("", "_blank")` returns **`null`** when the browser refuses
   even a click-initiated open. Desktop browsers allow it; some in-app browsers
   (WhatsApp's on Android, where many of these PDFs will be shared from) and
   strict mobile settings do not. The brief handles a fetch error but not a
   `null` tab. Rule: `tab === null` → fall through to the Download path (the
   `<a download>` anchor), so the user still gets the file.
2. **Revoking.** § 6.3 revokes object URLs when the list reloads, when `:id`
   changes and on unmount. The PDF's URL is assigned to `tab.location` after
   the fetch; if the user taps another equipment before the tab has finished
   loading the blob (a 10 MB manual on mobile data), the URL is revoked under
   the viewer and the tab shows an error. Rule: URLs of PDFs opened in a tab
   are kept until unmount (a few MB each — acceptable) or revoked in the tab's
   `load` event; the per-list revoke applies to thumbnails and the large
   photo only.

**Recommendation:** both rules into § 6.3; a one-line manual check "Open a PDF
from inside the WhatsApp browser" is optional.

### BR2-06 — minor — § 5.7: the PUT validator's integer rule; no record of who changed the limit; where `get_setting_int` lives

**Problem.**
1. **Validator.** "An integer 1–100 else 400" leaves JSON `true`, `20.0` and
   `"20"` to the coder. The existing validators (`equipment_core` line 58/75,
   `masters_core` line 79) use `isinstance(raw, int) and not isinstance(raw,
   bool)`; say the same here so the test for `"abc"` also covers `true` and
   `20.5`. The body is JSON, so `clean_body` with a small validator applies
   (a function in `settings.py` is enough; no `settings_core.py` for one
   field).
2. **Who changed it.** `app_settings` (v1) has `updated_at ON UPDATE` and no
   `updated_by`; the v2 audit convention says "never a time without an actor".
   Changing the upload limit is an IT-admin action. ISO 27001 **A.8.15
   (logging)** — in plain terms: record who did what and when for actions that
   matter — asks for at least a log line. Cheapest: the PUT route logs at INFO
   "upload_max_mb 20 → 50 by <user>". Optional and one statement in v6:
   `ALTER TABLE app_settings ADD COLUMN IF NOT EXISTS updated_by VARCHAR(100)
   NULL`, which brings the table to the convention before later settings use it.
3. **Placement.** `documents.py` importing `get_setting_int` from `settings.py`
   imports a blueprint module (it pulls `local_db.db_status` and Flask) for one
   helper. Round 1 offered `db_helpers.py` as well; that is the neutral home
   for "the first `app_settings` reader". Either works — pick and state it.

The RBAC side is consistent: `settings:read` = manager + IT admin,
`settings:edit` = IT admin (`config_rbac.py` lines 52–53), the nav item needs
`settings:read` (`navigation.js`), `test_rbac.test_role_matrix` is unaffected
(no new keys), `test_modules.TestSettingsDbStatus` is unaffected, and engineers
get `upload_max_mb` from the documents list, not from `/api/settings/app`.

**Recommendation:** add the integer rule and the log line; decide the home.

---

## Nit

### BR2-07 — nit — small things the coder would otherwise guess

- **Test data folder.** `os.environ["DATA_DIR"] = tempfile.mkdtemp(...)` leaves
  one folder per run under `%TEMP%`; hold a `tempfile.TemporaryDirectory()` at
  module level in `conftest.py` so it is removed at exit.
- **The 413 message** "The file is larger than 100 MB" is a second copy of the
  ceiling; build it from `MAX_CONTENT_LENGTH` so the two cannot drift.
- **`.gitignore`** has a section "Application data" (`scratch/`); `data/` goes
  there.
- **Settings tests file.** § 3 says `test_settings_api.py` "(or the existing
  settings test file)"; the existing one is `test_modules.py`
  (`TestSettingsDbStatus`). Pick the new file.
- **List shape.** `GET …/documents` returns `{items, upload_max_mb}` with no
  `total`; the base convention wraps lists as `{items, total}`. Unpaged and
  small, so fine — one clause saying so keeps the code reviewer quiet.
- **Dockerfile.** With uid 1000, `ENV PYTHONDONTWRITEBYTECODE=1` stops the
  harmless failed `__pycache__` writes under root-owned `/app`.
- **Standards, for the owner (§ 2).** "Remove hides, never deletes" follows
  ISO 55001 7.6.3; ISO 27001 **A.8.10 (information deletion)** pulls the other
  way — information no longer required should be deleted — and A.5.34 does the
  same for the EXIF position in photos. The two are reconciled by a retention
  rule ("removed documents are purged after N years"), which belongs with the
  out-of-scope "screen for removed documents". Worth one sentence so the
  deliberate v1 choice (keep everything) is on record as a choice.

---

## Checked and found consistent

- **Round-1 acceptances are in the text, not only in the log.** BR1-01: § 6.3
  synchronous `window.open`, `download` attribute, error path, revoking, blob
  URLs not shareable, Android + iPhone manual checks. BR1-02: Plan § 1 restated
  in § 6.1/§ 6.4/§ 7 ("MinIO (Plan § 1: no)"), same-filesystem rule for
  `os.replace`, App-FS backup, uid question (now BR2-01). BR1-03: § 5.3
  `formats=`, header pixel cap, exception list, `convert("RGB")`, thumbnail
  before the transaction, pure tests. BR1-04: § 5.7/§ 8 `GET`/`PUT
  /api/settings/app`, `get_setting_int` with bounds and a warning, Settings
  card, tests. BR1-05: JSON 413 handler, `upload_max_mb` in the list and the
  dialog, `content_length` before parsing, `read(limit + 1)`. BR1-06: one
  `try`, three-file clean-up, `OSError` → 503. BR1-07: public
  `load_node_for_user`/`LOCK_EQUIPMENT`, docstring note, conditional `UPDATE`,
  `UNIQUE_KEY_ERRORS` entry. BR1-08: `DATA_DIR` (adapted to the compose),
  `ENV` in the Dockerfile, set before `import config` in tests,
  `.dockerignore`. BR1-09: control characters, `send_file(download_name)`,
  `private` after `send_file`, `original_name` rule. BR1-10: EXIF to the user
  (§ 10.2), HEIC help line, `accept` without `capture`. BR1-11: ISO 14224
  Table 5 wording, ISO 55001 7.6.3, A.8.6/A.5.34/A.8.7, TPM steps 1–3, Pillow
  quarterly and no apt packages. BR1-12: `uv.lock`, form fields via
  `validate_document`, `ORDER BY created_at DESC, id DESC`, `saveLabel`
  "Upload", below Notes, `strict_slashes=False`, `formatBytes` with a test.
- **Production compose (HEAD).** `DATA_DIR: /app/data` and the bind mount
  `{{ nfs_mount_point }}:/app/data` are in the `x-backend` anchor shared by
  backend and worker, as § 6.4 says; `deploy.yaml` includes
  `app-fs/client/app-fs_setup.yaml` (user keytab owned by `base_username`,
  cron renewal, `/etc/fstab` mount). So `DATA_DIR` is the right env var name
  and no compose change is needed for the path.
- **Werkzeug 3.1.9 facts used by § 5.4/§ 6.2** (verified in the installed
  source): `send_file(download_name=…, as_attachment=False)` emits
  `Content-Disposition: inline` with `filename`/`filename*` (utils.py 460–461);
  `max_age > 0` sets `cache_control.public = True` (501–503), so the brief's
  "set `private` afterwards" is needed and correct; Flask's `send_file` has
  `conditional=True` by default (ETag/304).
- **413 handler.** `RequestEntityTooLarge` is an `HTTPException`;
  `app.register_error_handler` in `api_common.register_error_handlers` is the
  right place and the handler shape matches `{error, field?}`.
- **Duplicate-key mapping.** `_DUPLICATE_KEY_RE` matches
  `for key 'uq_equipment_documents_stored'` and the table-qualified form, so
  the `UNIQUE_KEY_ERRORS` entry works as `uq_equipment_code` does.
- **Transactions and 503.** `db_helpers.transaction` rolls back on any
  exception and re-raises, so an `ApiError(…, 503)` raised inside it reaches
  the handler after the rollback; `ApiError` carries any status.
- **Unit access and scrapped rule.** `load_node_for_user(for_update=False)`
  gives the same 404 for missing and not-at-your-units (S002 § 6); the 409 for
  scrapped is decided from the locking read; lock (1) is the start of the
  global order and `equipment_documents` rows are locked by nothing else, so
  the docstring's lock-order note extends without a cycle.
- **Migration v6.** `app_settings(setting_key VARCHAR(100) PK, setting_value
  TEXT)` exists from v1, so `INSERT IGNORE … ('upload_max_mb', '20')` is right;
  `CREATE TABLE IF NOT EXISTS` is safe to re-run as the v5 comment requires;
  audit columns match the v2 convention; `test_modules` compares against
  `LATEST_VERSION`, so v6 passes; `ix_equipment_documents_node (equipment_id,
  removed_at)` also serves the foreign key.
- **Conftest.** `_TABLES` runs with `FOREIGN_KEY_CHECKS = 0`, so adding
  `equipment_documents` anywhere in the tuple is enough; the
  `test_a_failure_after_the_counter_bump_rolls_it_back` monkeypatch pattern
  transfers to "insert failure → no file left" and "storage `OSError` → 503".
- **Frontend.** `api.js` returns `null` for non-JSON responses, so `apiGetBlob`
  must be a separate function, as § 3 says; `apiDelete` works for the 204; the
  Vite proxy forwards `/api` to 5001, so blob fetches work in dev;
  `FormModal` has no `saveLabel` today (the prop is new, as stated);
  `EquipmentDetailView` reloads on `:id` change via `watch`, so the documents
  component must follow the same rule (§ 6.3 says it does).
- **Nginx.** `client_max_body_size 100M` sits in the `/api/` location;
  `nosniff` is added by nginx in production and by the route in dev.
- **Permissions and Plan § 3.** No new keys; upload/remove on `equipment:edit`
  (engineer, IT admin), read on `equipment:read` (`*`), the limit on
  `settings:*` — matches the matrix. Operators see and open documents (§ 10.5).
- **Plan § 5.** `equipment_documents` is listed for equipment; tickets and jobs
  get `attachments` later, reusing `file_store` not the table — consistent.
- **Standards (§ 2).** ISO 55001 7.5/7.6/7.6.3; ISO 14224 Table 5 (equipment
  data: manufacturer, model, design data — the manual is the source);
  ISO 27001:2022 A.5.12, A.5.34, A.8.3, A.8.6, A.8.7, A.8.13, A.8.28 — all
  correctly numbered and described in plain terms; TPM autonomous-maintenance
  steps 1–3 and visual controls. A.8.15 (logging) and A.8.10 (deletion) are
  the two additions suggested above.
- **Out-of-scope list and § 7 decisions** match Plan phase 2 and are
  proportionate; HEIC, Office, DWG, SVG stay out for the reasons given in r1.
