"""Documents and photos on equipment (docs/steps/S006-equipment-documents/1-brief.md).

Thin shell: documents_core holds the rules (file type from the first bytes, titles,
names, thumbnails); file_store does the file I/O; this module checks unit access and
the scrapped rule, orders the writes and serves files.

Upload order (brief § 5.6): every check and the thumbnail first, then the files are
written with no transaction open, then a short transaction locks the node (lock (1) of
equipment.py's order, the only lock taken here), re-checks scrapped from the locked row
and inserts.  So a hanging NFS mount never holds the node lock, and Pillow never runs
under it.  If the transaction fails, the files just written are removed.

Files are served only through these routes, after the access check (ISO 27001 A.8.3).
A removed document keeps its row and its file (ISO 55001 controlled information) but is
no longer listed or served.  A removed document can be restored or deleted for good by
equipment:purge_documents (S008).
"""

import logging
import secrets

from flask import Blueprint, jsonify, request, send_file

import file_store
from api_common import (
    DEFAULT_PER_PAGE, MAX_PAGE, MAX_PER_PAGE, UNIQUE_KEY_ERRORS, ApiError, actor, clean_body, enum_arg, int_arg,
    like_pattern,
)
from auth_utils import require_perm
from config import MB
from db_helpers import count, get_db, insert_row, row_to_dict, transaction, update_row
from documents_core import (
    KINDS, SIGNATURE_BYTES, THUMB_EXTENSION, TYPE_REFUSED, FILE_TYPES, PhotoTooLarge, clean_original_name,
    detect_file_type, kind_accepts, make_thumbnail, safe_download_name, stored_name, thumb_name,
    validate_document, validate_title,
)
from equipment import NODE_JOINS, accessible_unit_ids, load_node_for_user, node_path
from equipment_core import SCRAPPED
from settings import upload_max_mb

logger = logging.getLogger(__name__)

documents_bp = Blueprint("documents", __name__)

UNIQUE_KEY_ERRORS.update({
    "uq_equipment_documents_stored": (None, "Retry the upload"),
})

# Room for the multipart boundaries and the kind and title fields on top of the file
FORM_FIELDS_ALLOWANCE = 64 * 1024

STORED_TOKEN_BYTES = 16   # 32 hex characters

CACHE_MAX_AGE_S = 3600

SCRAPPED_MESSAGE = "This record is scrapped and cannot be changed"
STORAGE_UNAVAILABLE = "File storage is unavailable — try again later"
FILE_LEFT_BEHIND = ("The record is deleted, but its file could not be removed from storage. "
                    "Ask IT to remove it; the path is in the server log.")

_ITEM_COLUMNS = ("id, kind, title, original_name, content_type, size_bytes, has_thumb,"
                 " created_at, created_by, updated_at, updated_by")


def _item(row):
    """A row as the API shows it.  The stored name is internal (a path part) and never
    goes to the client."""
    item = row_to_dict({key: value for key, value in row.items() if key != "stored_name"})
    item["has_thumb"] = bool(item["has_thumb"])
    return item


def _read_item(cur, node_id, doc_id):
    """A document of this node that is not removed, as listed; None otherwise."""
    cur.execute(f"SELECT {_ITEM_COLUMNS}, stored_name FROM equipment_documents "
                "WHERE id = %s AND equipment_id = %s AND removed_at IS NULL", (doc_id, node_id))
    return cur.fetchone()


def _lock_node_for_change(cur, node_id):
    """Lock the node (1) and refuse a scrapped one from the locked row (S002 BR3-01)."""
    locked, _ = load_node_for_user(cur, node_id, for_update=True)
    if locked["status"] == SCRAPPED:
        raise ApiError(SCRAPPED_MESSAGE, 409)


# ---------------------------------------------------------------------------
# List and upload
# ---------------------------------------------------------------------------

@documents_bp.route("/<int:node_id>/documents", strict_slashes=False)
@require_perm("equipment:read")
def list_documents(node_id):
    with get_db().cursor() as cur:
        load_node_for_user(cur, node_id, for_update=False)
        cur.execute(f"SELECT {_ITEM_COLUMNS} FROM equipment_documents "
                    "WHERE equipment_id = %s AND removed_at IS NULL ORDER BY created_at DESC, id DESC",
                    (node_id,))
        items = [_item(row) for row in cur.fetchall()]
        return jsonify({"items": items, "upload_max_mb": upload_max_mb(cur)})


def _read_upload(limit_mb):
    """The checks of brief § 5.6 step 2 -> (clean form fields, file bytes, file type,
    thumbnail or None, original name).  Raises ApiError."""
    limit = limit_mb * MB
    too_large = ApiError(f"The file is larger than {limit_mb} MB", 400, "file")
    # Before request.form / request.files: Werkzeug spools the whole body on first access.
    # A chunked request has no length; the read below still applies.
    if request.content_length is not None and request.content_length > limit + FORM_FIELDS_ALLOWANCE:
        raise too_large
    clean, errors = validate_document(request.form)
    if errors:
        raise ApiError(errors[0]["message"], 400, errors[0]["field"])
    upload = request.files.get("file")
    if upload is None:
        raise ApiError("Choose a file", 400, "file")
    data = upload.read(limit + 1)   # + 1 tells "exactly at the limit" from "over it"
    if len(data) > limit:
        raise too_large
    if not data:
        raise ApiError("The file is empty", 400, "file")
    detected = detect_file_type(data[:SIGNATURE_BYTES])
    if detected is None or not kind_accepts(clean["kind"], detected[0]):
        raise ApiError(TYPE_REFUSED, 400, "file")
    original_name = clean_original_name(upload.filename, clean["title"])
    thumb = None
    if clean["kind"] == "photo":
        try:
            thumb = make_thumbnail(data)
        except PhotoTooLarge as exc:
            raise ApiError(str(exc), 400, "file") from exc
    return clean, data, detected[0], thumb, original_name


def _write_files(node_id, name, data, thumb):
    """Brief § 5.6 step 3, no transaction open -> the paths written.  A storage error
    removes what was written and becomes a 503."""
    written = []
    try:
        written.append(file_store.write_file(node_id, name, data))
        if thumb is not None:
            written.append(file_store.write_file(node_id, thumb_name(name), thumb))
    except OSError as exc:
        for path in written:
            file_store.remove_quietly(path)
        logger.error("File storage write failed for node %s: %s (errno %s, %s)",
                     node_id, exc.filename, exc.errno, exc.strerror)
        raise ApiError(STORAGE_UNAVAILABLE, 503) from exc
    return written


@documents_bp.route("/<int:node_id>/documents", methods=["POST"], strict_slashes=False)
@require_perm("equipment:edit")
def upload_document(node_id):
    conn = get_db()
    # Step 1 — plain read: access (404) and an early scrapped check, so a scrapped node
    # gets no file read or written.  The decision that counts is the locked one below.
    with conn.cursor() as cur:
        _, node = load_node_for_user(cur, node_id, for_update=False)
        if node["status"] == SCRAPPED:
            raise ApiError(SCRAPPED_MESSAGE, 409)
        limit_mb = upload_max_mb(cur)

    clean, data, file_type, thumb, original_name = _read_upload(limit_mb)   # step 2
    if clean["kind"] == "photo" and thumb is None:
        logger.warning("No thumbnail for a photo on node %s (%s): Pillow could not read it",
                       node_id, original_name)
    content_type, ext = FILE_TYPES[file_type]
    name = stored_name(secrets.token_hex(STORED_TOKEN_BYTES), ext)
    written = _write_files(node_id, name, data, thumb)                     # step 3

    try:                                                                    # step 4
        with transaction(conn), conn.cursor() as cur:
            _lock_node_for_change(cur, node_id)   # (1); 404 (access, from the locked state); 409
            doc_id = insert_row(cur, "equipment_documents", {
                "equipment_id": node_id,
                "kind": clean["kind"],
                "title": clean["title"],
                "original_name": original_name,
                "stored_name": name,
                "content_type": content_type,
                "size_bytes": len(data),
                "has_thumb": int(thumb is not None),
            }, actor())
            # Read inside the transaction: a remove landing after the commit cannot turn
            # this response into a 500
            item = _item(_read_item(cur, node_id, doc_id))
    except BaseException:
        # Step 5 — any failure leaves no file behind; the original error is what the user gets
        for path in written:
            file_store.remove_quietly(path)
        raise

    return jsonify(item), 201


# ---------------------------------------------------------------------------
# Serving
# ---------------------------------------------------------------------------

def _serve(node_id, doc_id, thumbnail):
    with get_db().cursor() as cur:
        load_node_for_user(cur, node_id, for_update=False)
        doc = _read_item(cur, node_id, doc_id)
    if doc is None or (thumbnail and not doc["has_thumb"]):
        raise ApiError("Not found", 404)
    if thumbnail:
        name, content_type, ext = thumb_name(doc["stored_name"]), "image/jpeg", THUMB_EXTENSION
    else:
        name, content_type = doc["stored_name"], doc["content_type"]
        ext = name.rsplit(".", 1)[1]
    path = file_store.file_path(node_id, name)
    if not file_store.is_file(path):
        # The row is there but the file is not: the mount or the backup is wrong
        logger.error("File missing for document %s of node %s: %s", doc_id, node_id, path)
        raise ApiError("File missing", 404)
    response = send_file(path, mimetype=content_type, download_name=safe_download_name(doc["title"], ext),
                         conditional=True, max_age=CACHE_MAX_AGE_S)
    response.headers["X-Content-Type-Options"] = "nosniff"
    # send_file marks a max_age response public; these files are per-user (unit access)
    response.cache_control.public = False
    response.cache_control.private = True
    return response


@documents_bp.route("/<int:node_id>/documents/<int:doc_id>/file")
@require_perm("equipment:read")
def get_document_file(node_id, doc_id):
    return _serve(node_id, doc_id, thumbnail=False)


@documents_bp.route("/<int:node_id>/documents/<int:doc_id>/thumb")
@require_perm("equipment:read")
def get_document_thumb(node_id, doc_id):
    return _serve(node_id, doc_id, thumbnail=True)


# ---------------------------------------------------------------------------
# Edit title, remove
# ---------------------------------------------------------------------------

def _validate_title_body(body, _creating):
    """Only the title; any other key is ignored, so the file, kind and node never change."""
    title, message = validate_title(body.get("title"))
    return {"title": title}, ([{"field": "title", "message": message}] if message else [])


@documents_bp.route("/<int:node_id>/documents/<int:doc_id>", methods=["PUT"])
@require_perm("equipment:edit")
def update_document_title(node_id, doc_id):
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        _lock_node_for_change(cur, node_id)   # (1); 404; 409
        clean = clean_body(_validate_title_body, creating=False)
        # The SELECT decides the 404, not rowcount: MariaDB counts an unchanged row as
        # 0 affected, so saving the same title would look like a missing document.  The node
        # lock serialises this with remove.
        if _read_item(cur, node_id, doc_id) is None:
            raise ApiError("Not found", 404)
        update_row(cur, "equipment_documents", doc_id, clean, actor())
        item = _item(_read_item(cur, node_id, doc_id))   # still under the node lock
    return jsonify(item)


@documents_bp.route("/<int:node_id>/documents/<int:doc_id>", methods=["DELETE"])
@require_perm("equipment:edit")
def remove_document(node_id, doc_id):
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        _lock_node_for_change(cur, node_id)   # (1); 404; 409
        # One conditional statement: two removes at once give one 204 and one 404
        cur.execute("UPDATE equipment_documents SET removed_at = NOW(), removed_by = %s "
                    "WHERE id = %s AND equipment_id = %s AND removed_at IS NULL", (actor(), doc_id, node_id))
        if cur.rowcount == 0:
            raise ApiError("Not found", 404)
    return "", 204


# ---------------------------------------------------------------------------
# Removed documents: list, restore, delete for good (S008)
# ---------------------------------------------------------------------------

_REMOVED_COLUMNS = (
    "SELECT d.id, d.kind, d.title, d.original_name, d.content_type, d.size_bytes, d.created_at,"
    " d.created_by, d.removed_at, d.removed_by, e.id AS equipment_id, e.code, e.name, e.level, e.status,"
    " s.code AS site_code, u.code AS unit_code, p.code AS p_code, gp.code AS gp_code"
)
# An inner join: right while every document belongs to a node
_REMOVED_FROM = " FROM equipment_documents d JOIN equipment e ON e.id = d.equipment_id" + NODE_JOINS

_PATH_COLUMNS = ("site_code", "unit_code", "p_code", "gp_code")


def _removed_item(row):
    """A removed-list row as the API shows it: the node's unit and path instead of the
    join columns they come from."""
    item = row_to_dict({key: value for key, value in row.items() if key not in _PATH_COLUMNS})
    item["unit"] = f"{row['site_code']}.{row['unit_code']}"
    item["full_path"] = node_path(row)
    return item


@documents_bp.route("/removed-documents")
@require_perm("equipment:purge_documents")
def list_removed_documents():
    page = int_arg("page", 1, minimum=1, maximum=MAX_PAGE)
    per_page = int_arg("per_page", DEFAULT_PER_PAGE, minimum=1, maximum=MAX_PER_PAGE)
    conditions, params = ["d.removed_at IS NOT NULL"], []
    kind = enum_arg("kind", KINDS)
    if kind:
        conditions.append("d.kind = %s")
        params.append(kind)
    q = (request.args.get("q") or "").strip()
    if q:
        # The original name too: phone photos are IMG_2034 in both title and file name
        conditions.append("(e.code LIKE %s OR d.title LIKE %s OR d.original_name LIKE %s)")
        params.extend([like_pattern(q)] * 3)

    with get_db().cursor() as cur:
        unit_ids = accessible_unit_ids(cur)
        if unit_ids is not None:
            if not unit_ids:
                return jsonify({"items": [], "total": 0, "page": page, "per_page": per_page})
            conditions.append(f"u.id IN ({', '.join(['%s'] * len(unit_ids))})")
            params.extend(sorted(unit_ids))
        where = f" WHERE {' AND '.join(conditions)}"
        total = count(cur, f"SELECT COUNT(*) AS n{_REMOVED_FROM}{where}", params)
        cur.execute(f"{_REMOVED_COLUMNS}{_REMOVED_FROM}{where} ORDER BY d.removed_at DESC, d.id DESC "
                    "LIMIT %s OFFSET %s", [*params, per_page, (page - 1) * per_page])
        items = [_removed_item(row) for row in cur.fetchall()]
    return jsonify({"items": items, "total": total, "page": page, "per_page": per_page})


@documents_bp.route("/<int:node_id>/documents/<int:doc_id>/restore", methods=["POST"])
@require_perm("equipment:purge_documents")
def restore_document(node_id, doc_id):
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        _lock_node_for_change(cur, node_id)   # (1); 404; 409
        cur.execute("SELECT id, title, kind, removed_by, removed_at FROM equipment_documents "
                    "WHERE id = %s AND equipment_id = %s AND removed_at IS NOT NULL", (doc_id, node_id))
        doc = cur.fetchone()
        if doc is None:
            raise ApiError("Not found", 404)
        # updated_at / updated_by record the last title edit, not a restore
        cur.execute("UPDATE equipment_documents SET removed_at = NULL, removed_by = NULL WHERE id = %s", (doc_id,))
        item = _item(_read_item(cur, node_id, doc_id))   # still under the node lock
    logger.info("Document %s '%s' (%s) of node %s restored by %s; removed by %s at %s",
                doc_id, doc["title"], doc["kind"], node_id, actor(), doc["removed_by"], doc["removed_at"])
    return jsonify(item)


def _remove_stored_files(node_id, doc):
    """Delete the file and its thumbnail, each attempted on its own -> True when every file
    is gone (or was already missing).  Logs what it finds; never raises."""
    names = [doc["stored_name"]]
    if doc["has_thumb"]:
        names.append(thumb_name(doc["stored_name"]))
    all_gone = True
    for name in names:
        path = file_store.file_path(node_id, name)
        try:
            if not file_store.remove_file(path):
                # The same sign _serve logs: the mount or the backup is wrong.  The outcome is fine.
                logger.warning("File already missing when deleting document %s of node %s: %s",
                               doc["id"], node_id, path)
        except OSError as exc:
            all_gone = False
            logger.error("Could not delete file %s of document %s, node %s: errno %s, %s",
                         path, doc["id"], node_id, exc.errno, exc.strerror)
    return all_gone


@documents_bp.route("/<int:node_id>/documents/<int:doc_id>/purge", methods=["POST"])
@require_perm("equipment:purge_documents")
def purge_document(node_id, doc_id):
    conn = get_db()
    # Row first, then the files (brief § 5.3): after the commit nothing can restore the
    # document, so a file is never deleted from under a live row.
    with transaction(conn), conn.cursor() as cur:
        # No scrapped check: erasing a file is disposition of information, not a change to
        # the asset record
        load_node_for_user(cur, node_id, for_update=True)   # (1); 404
        cur.execute("SELECT id, title, kind, stored_name, has_thumb, created_by, removed_by, removed_at "
                    "FROM equipment_documents WHERE id = %s AND equipment_id = %s", (doc_id, node_id))
        doc = cur.fetchone()
        if doc is None:
            raise ApiError("Not found", 404)
        if doc["removed_at"] is None:
            raise ApiError("Remove the document first", 409)
        cur.execute("DELETE FROM equipment_documents WHERE id = %s AND equipment_id = %s", (doc_id, node_id))
    # After the commit, so it is never logged for a rolled-back delete, and before the file
    # I/O, so it is there even if that hangs
    logger.info("Document %s '%s' (%s, %s) of node %s deleted for good by %s; uploaded by %s, removed by %s at %s",
                doc_id, doc["title"], doc["kind"], doc["stored_name"], node_id, actor(), doc["created_by"],
                doc["removed_by"], doc["removed_at"])
    if not _remove_stored_files(node_id, doc):
        return jsonify({"warning": FILE_LEFT_BEHIND})
    return "", 204
