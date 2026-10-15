```
Step: S006 — Documents and photos on equipment
Doc: brief-review r3
Author: Brief reviewer (Fable)
Date: 15-10-2026
```

# S006 — Brief review, round 3

**Verdict: no `blocker` or `major` finding is open.** Every round-2 finding
marked `Accepted` is in the brief's text, not only in the Review log (checked
item by item; list at the end). The round-2 revisions are sound: the reordered
§ 5.6 holds no lock during file I/O and cleans up correctly, the § 5.2 ceilings
and checks are consistent with Werkzeug 3.1.9 and the Nginx config, the § 5.3
order is right, and § 6.4 matches the devops working tree. What is left is two
`minor` points (one Pillow fact in § 5.3 that does not do what the brief says
it does; one § 9 test that would pass for the wrong reason as written) and
four nits.

Reviewed against the working tree (S005 uncommitted): `backend/equipment.py`
(`_LOCK_EQUIPMENT` line 95, `_load_node_for_user` line 219; the tests patch only
`_read_node`, `_write_events`, `insert_row`, `update_row`, so the renames break
nothing), `db_helpers.py`, `api_common.py`, `app.py`, `config.py`, `settings.py`,
`tests/conftest.py`, `tests/test_equipment_api.py`; installed Werkzeug 3.1.9
(`wsgi.get_input_stream`, `sansio.utils.get_content_length`,
`sansio.request.content_length`, `test.EnvironBuilder`); `tooling/build/
Dockerfile.backend`, `nginx.conf`, `gunicorn.conf.py`, `.dockerignore`,
`.gitignore`; `smtw_erp_devops/erp_server/yantra/compose.yml.j2` (working tree),
`deploy.yaml`, `app-fs/client/app-fs_setup.yaml`, `git status` of that repo.
Settings and secrets files were **not** read. Pillow is not installed yet
(`uv add pillow` is the coder's), so the Pillow facts below are from its
documented behaviour, not the local source. Docs: `Plan.MD` § 1/§ 5,
`SMTW-WebApp-Base.md` § API Response Conventions / File Upload / Object Storage,
CLAUDE-COMMON, CLAUDE.md.

---

## Minor

### BR3-01 — minor — § 5.3: `convert("RGB")` does not flatten a transparent PNG on white; it drops the alpha channel

**Problem.** § 5.3 step 3 says `convert("RGB")` "(a transparent PNG is
flattened on white, since JPEG has no transparency)". Pillow's RGBA → RGB
conversion simply discards the alpha channel; the colour stored under
transparent pixels is kept, and most encoders store black there. A drawing or
logo on a transparent background therefore gets a **black** background in its
thumbnail, not white. Palette (`P`) PNGs with a `transparency` entry behave the
same way. The § 9 test "an RGBA PNG gives a thumbnail" passes either way, so
nothing would catch it.

**Why it matters.** Drawings exported as PNG are a common photo-kind upload
(§ 1 lists drawings); a black thumbnail of a line drawing is unreadable, and
the coder follows the brief's sentence as written. Small, but it is exactly
the kind of fact the brief exists to settle.

**Options.**
1. Replace the `convert("RGB")` step with a flatten rule: if the image has
   alpha (`mode in ("RGBA", "LA")` or `"transparency" in info`), convert to
   `RGBA`, create `Image.new("RGB", size, "white")` and `paste(img, mask=alpha)`;
   otherwise `convert("RGB")`. Five lines, still after `thumbnail` and
   `exif_transpose`, so the memory argument of § 5.3 is unchanged (the flatten
   runs on the 400 px result). Extend the § 9 pure test: an RGBA PNG whose
   corner is fully transparent gives a thumbnail whose corner pixel is white.
2. Keep `convert("RGB")` and state "transparent areas may come out black" as
   accepted.

**Recommendation:** option 1. Side note for the coder, no rule needed: Pillow
resizes `P`-mode images with nearest-neighbour, so a palette PNG's thumbnail is
a little jagged; converting to `RGBA` *before* `thumbnail` for non-JPEG images
fixes that at no memory cost (PNG and WebP decode in full anyway; only JPEG
benefits from `thumbnail` running first). Either is acceptable.

### BR3-02 — minor — § 9 "No `Content-Length` (a chunked request in the test client)": as written, the test passes for the wrong reason

**Problem.** The Flask test client always sets `CONTENT_LENGTH` for multipart
data (`EnvironBuilder`, `test.py` 692–744) and never sets
`wsgi.input_terminated`. Werkzeug 3.1.9's `get_input_stream` (verified in the
installed source) returns an **empty** stream when the length is unknown and
the server has not marked the input as terminated. So a test that removes the
header gets a body with no file part → 400 "Choose a file" — a 400 with field
`file`, which the test as described ("still refused above the limit by
check 3") would accept as a pass while check 3 never ran.

**Why it matters.** The brief promises a behaviour (an unknown-length upload is
still bounded by check 3) and the test is its only proof. A test that passes
on an empty body proves nothing and would hide a regression.

**Options.**
1. State the recipe in § 9: send the multipart body with
   `environ_overrides={"HTTP_TRANSFER_ENCODING": "chunked", "wsgi.input_terminated": True}`.
   The `Transfer-Encoding: chunked` header makes `request.content_length`
   `None` (so check 2 is skipped, as § 5.2 says), and `wsgi.input_terminated`
   makes Werkzeug read the stream (bounded by `MAX_CONTENT_LENGTH`, as in
   production under gunicorn). Assert the message "The file is larger than
   N MB", not only the status.
2. Drop the test and keep the rule.

**Recommendation:** option 1, with the assertion on the message. For the
record (no change needed): in production Nginx buffers the request body
(`proxy_request_buffering` default on) and forwards it with a `Content-Length`,
so check 2 always runs there; the chunked path is only curl and scripts, as
BR2-02 said.

---

## Nit

### BR3-03 — nit — § 5.6: the "early" scrapped check comes after the file is parsed, read and thumbnailed

Step 2 ends with "Early scrapped check from the plain read of step 1 (409)",
but step 2 begins with validating, reading the file up to the limit, detecting
the type and making the thumbnail. The check costs nothing (the plain read of
step 1 already has `status`), so it belongs in step 1 right after the 404,
before the size check: a scrapped node then refuses on the headers alone, and
the order 404 → 409 → 400 matches `update_equipment`, which refuses scrapped
before validating the body. The brief's guarantee ("a scrapped node doesn't
get files written at all") holds either way; this only saves the work.

### BR3-04 — nit — the 413 message's number: § 3 names two different constants

§ 3 (`api_common.py`) says the number is "taken from the setting's ceiling
constant" (100); § 3 (`app.py`) says `MAX_CONTENT_LENGTH = 101 MB` comes "from
one constant that the 413 message also uses" (101). The user-facing number
should be 100 (the largest file that can ever be accepted); the ceiling is
derived. Suggested wording: one constant `UPLOAD_MAX_MB_CEILING = 100` (in
`settings.py`, where `get_setting_int(…, 1, 100)` already needs it);
`app.py` sets `MAX_CONTENT_LENGTH = (UPLOAD_MAX_MB_CEILING + 1) * 1024 * 1024`
and the 413 handler says "larger than {UPLOAD_MAX_MB_CEILING} MB". In the § 9
413 test the message will still say 100 MB although the app ceiling was lowered
for the test — assert the shape `{error, field}`, as the brief already says.

### BR3-05 — nit — § 6.4 says the container-user change is "done"; it is prepared, uncommitted

`git status` in `smtw_erp_devops` still shows `M erp_server/yantra/compose.yml.j2`
and `M erp_server/yantra/vars/example_settings_vel_yantra_master.yaml`
(the second not read). The compose working tree has `user: "1000:1000"` with
the comment § 6.4 describes, so the brief's facts are right; one phrase keeps
it truthful: "in the devops working tree, uncommitted; the user commits it with
the S006 deploy". The `deploy.yaml` facts are verified: `secrets_app.py` is
templated with `owner: base_username`, `mode: '0600'` (lines 56–61); the
user-ticket renewal cron runs as `base_username` every 6 h
(`app-fs_setup.yaml` 82–88).

### BR3-06 — nit — small things the coder would otherwise guess

- **The 64 MP header for the § 9 cap tests.** Do not build an 8 000 × 8 000
  image (192 MB in the test process, and slow). Take a 1 × 1 JPEG from Pillow
  and overwrite the height and width in its SOF0 segment (the four bytes after
  `FF C0`, length and precision): Pillow reads `size` from that header without
  decoding, so the cap fires on `img.size` and the body is never touched. A
  patched PNG would also need its IHDR CRC recomputed, so JPEG is the cheap
  one. No `DecompressionBombWarning` appears below 89.5 MP, so the test output
  stays clean.
- **`safe_download_name`** is a rule in § 5.4 and a test in § 9 but is missing
  from § 3's list of `documents_core.py` functions; add it there.
- **Thumbnail download name.** § 6.2 says `…/thumb` carries the download name
  of § 5.4; for a thumbnail that is `<title>.jpg` regardless of the original's
  type — one word in § 6.2 so the coder does not reuse the original's
  extension.

---

## Checked and found consistent

- **Round-2 acceptances are in the text, not only in the log.** BR2-01: § 6.4
  states the `user: "1000:1000"` change and its comment, the `0600` /
  `base_username` consequence, the `id <base_username>` check, the write test;
  § 10.1 reduced to the ownership check; `PYTHONDONTWRITEBYTECODE` in § 3.
  BR2-02: § 5.2 check 2 skipped when `content_length` is missing; ceilings at
  101 MB in § 3 (`nginx.conf`, `app.py`), § 5.2 and § 7; the 413 called a
  backstop with the reason (enforced only when `request.files` is read — true
  of Werkzeug 3.1.9, verified); the § 9 413 test lowered **below** the setting.
  BR2-03: § 9 uses 8 000 × 8 000; § 5.3 step 3 is `thumbnail` → `exif_transpose`
  → RGB, with the reason; the 200 MB worst case stated against A.8.6. BR2-04:
  § 5.6 steps 1–5 (plain read first, files written with no transaction open,
  short lock-then-insert transaction, clean-up on any failure of step 4), the
  "clean-up never hides the real error" rule, path and errno in the ERROR line,
  the orphan-file acceptance, the lock note; § 7 row added. BR2-05: § 6.3
  `window.open` `null` → Download; PDF URLs revoked on unmount only. BR2-06:
  § 3/§ 5.7 JSON integer only (not bool, float, string), INFO log with actor
  and old/new (A.8.15), helper in `settings.py`. BR2-07: temp folder removed at
  session end; `.gitignore` "Application data"; `test_settings_api.py`; "no
  `total`" with the reason in § 8; A.8.10 reconciled with ISO 55001 in § 2.
- **§ 5.6 order is safe.** Step 1's plain read runs on the autocommit pooled
  connection, so no snapshot or lock is held while the files are written; step 4
  takes lock (1) through `LOCK_EQUIPMENT`, decides scrapped from the locked row
  (the S002 rule), and `db_helpers.transaction` rolls back on any exception
  including an `ApiError(…, 409)`, so step 5's clean-up and re-raise give the
  user the 409 and leave nothing on disk. `equipment_documents` rows are locked
  by nothing else, so the docstring's lock-order note extends without a cycle.
  A node scrapped between steps 1 and 4 costs one write-and-delete — rare,
  harmless, stated.
- **§ 5.3 order is correct.** `Image.open` is lazy, so `img.size` for the cap
  reads the header only; `thumbnail()` keeps `img.info` (the EXIF block), so
  `exif_transpose` after it still sees the orientation tag and transposes the
  400 px result; `formats=["JPEG", "PNG", "WEBP"]` is a real `Image.open`
  parameter; Pillow's own `DecompressionBombError` threshold is 2 × 89.5 MP,
  above the 50 MP cap, so the cap always answers first and the backstop is
  reachable only by a crafted header.
- **§ 5.2 checks and ceilings.** Nothing before the route touches the body
  (`require_auth` reads headers; `clean_body` is not used for multipart; the
  only `request.get_json` calls are in `clean_body` and `masters.py`), so check 2
  really runs before Werkzeug spools. Nginx `101M` and Flask `101 × 1024 × 1024`
  are the same number; a 100 MB file plus a few hundred bytes of multipart
  framing passes both; check 3's `read(limit + 1)` tells "at" from "over".
  Werkzeug spools to `/tmp`, which uid 1000 can write in `python:3.12-slim`.
- **The renames in `equipment.py`** (`load_node_for_user`, `LOCK_EQUIPMENT`)
  touch no test: the suite patches `_read_node`, `_write_events`, `insert_row`
  and `update_row` only.
- **Container as uid 1000.** The image has no `USER`; `uv sync` and `COPY`
  run as root, so `/app` is readable and not writable by 1000 — hence
  `PYTHONDONTWRITEBYTECODE`; gunicorn writes only to stdout/stderr; the
  bind mount and `DATA_DIR: /app/data` sit in the shared `x-backend` anchor, so
  backend and worker see the same path.
- **Base pattern.** § File Upload Pattern is followed point by point (magic
  bytes, system-generated names, authenticated route, `data/` gitignored, limit
  in `app_settings`); the one departure (no tenant level in the path) is
  stated in § 6.1 with the reason. The unpaged `{items, upload_max_mb}` is the
  stated departure from `{items, total}`.
- **Standards (§ 2, § 3), for the owner.** ISO 55001 7.5/7.6.3 (controlled
  information: who changed what, nothing lost silently); ISO 14224 Table 5
  (manufacturer, model, design data — the manual is the source); TPM autonomous
  maintenance steps 1–3 and visual controls (before/after and standard-condition
  photos); ISO 27001:2022 A.5.12 (classification), A.5.34 (privacy/PII),
  A.8.3 (access restriction), A.8.6 (capacity), A.8.7 (malware), A.8.10
  (deletion), A.8.13 (backup), A.8.15 (logging), A.8.28 (secure coding) — all
  correctly numbered, each explained in one plain sentence and tied to a rule
  in the brief. The deliberate gaps (no malware scan, EXIF kept, nothing
  purged) are stated as the user's decisions in § 10.
