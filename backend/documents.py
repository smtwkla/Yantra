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
no longer listed or served.
"""

import logging
import secrets

from flask import Blueprint, jsonify, request, send_file

import file_store
from api_common import UNIQUE_KEY_ERRORS, ApiError, actor, clean_body
from auth_utils import require_perm
from config import MB
from db_helpers import get_db, insert_row, row_to_dict, transaction, update_row
from documents_core import (
    SIGNATURE_BYTES, THUMB_EXTENSION, TYPE_REFUSED, FILE_TYPES, PhotoTooLarge, clean_original_name,
    detect_file_type, kind_accepts, make_thumbnail, safe_download_name, stored_name, thumb_name,
    validate_document, validate_title,
)
from equipment import load_node_for_user
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
