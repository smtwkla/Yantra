"""Documents and photos on equipment (docs/steps/S006-equipment-documents/1-brief.md), on a
node or, since S012, on an equipment model (docs/steps/S012-equipment-models; the owner
design of the dropped S009), and since S017 photos on a ticket (docs/steps/S017-raise-tickets),
since S018 its documents too (docs/steps/S018-work-tickets, user decision 5).

Thin shell: documents_core holds the rules (file type from the first bytes, titles,
names, thumbnails); file_store does the file I/O; this module checks access and the
scrapped rule, orders the writes and serves files.

Owners (OWNERS below): a document belongs to exactly one node, model or ticket (the owner
CHECK, v9 and v12).  Each operation is written once and takes ``(owner, owner_id)``; its URLs
are stacked route decorators whose ``defaults`` name the owner.  Each owner carries its keys
as data (S017 § 5.5); every owner takes every kind (S018 removed the ticket's photos-only rule): the route checks the owner's key held at any site
(check_perm), then the owner's read or lock function checks it at the record's site.  Node documents follow the
node's site and units (S011: unit access, and the write key checked at the node's site).
Model documents are visible to every user with equipment:read, at every site, and are
maintained by equipment:edit (restore and purge: equipment:purge_documents) held at any
site (S012 § 2, ISO 27001 A.8.3: a model's documents are generic maker information).  A
node's list also returns its model's documents as an ``inherited`` group, looked up live.
Ticket photos and documents follow the ticket's access predicate (tickets.py) and are added,
retitled and removed by ticket:raise at the ticket's site, never on a closed ticket (the ticket
page offers *Add document* to ticket:work holders only, S018 § 3).

Upload order (S006 § 5.6): every check and the thumbnail first, then the files are
written with no transaction open, then a short transaction locks the owner and inserts.
So a hanging NFS mount never holds a lock, and Pillow never runs under it.  If the
transaction fails, the files just written are removed.

Locks: a document write takes exactly one owner lock — the node row (lock (1) of
equipment.py's order, re-checking scrapped, access and the site key from the locked row),
the model row (4) or the ticket row (7, tickets.py's order) — and then only
equipment_documents rows, which nothing else locks.  It never holds two owner locks, so it
cannot join a cycle with equipment.py (node → … → model → class), masters.py (manufacturer →
model → class → type) or tickets.py (node → counter → ticket).  The owner lock also
serialises a title edit with a remove (S006 § 5.8).

Files are served only through these routes, after the access check (ISO 27001 A.8.3).
A removed document keeps its row and its file (ISO 55001 controlled information) but is
no longer listed or served.  A removed document can be restored or deleted for good by
equipment:purge_documents (S008), node, model and ticket documents alike (S012 § 5.6,
S017 § 5.5).
"""

import logging
import secrets
from collections.abc import Callable
from dataclasses import dataclass

from flask import Blueprint, jsonify, request, send_file

import file_store
from api_common import (
    DEFAULT_PER_PAGE, MAX_PAGE, MAX_PER_PAGE, UNIQUE_KEY_ERRORS, ApiError, actor, clean_body, enum_arg, int_arg,
    like_pattern,
)
from auth_utils import check_perm, require_perm
from config import MB
from db_helpers import count, get_db, insert_row, row_to_dict, transaction, update_row
from documents_core import (
    KINDS, SIGNATURE_BYTES, THUMB_EXTENSION, TYPE_REFUSED, FILE_TYPES, PhotoTooLarge, clean_original_name,
    detect_file_type, kind_accepts, make_thumbnail, safe_download_name, stored_name, thumb_name,
    validate_document, validate_title,
)
from equipment import NODE_JOINS, accessible_unit_ids, load_node_for_user, node_path
from equipment_core import SCRAPPED
from masters_core import model_label
from settings import upload_max_mb
from tickets import lock_ticket_for_change, lock_ticket_for_purge, read_ticket, read_ticket_for_change

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


# ---------------------------------------------------------------------------
# Owners — how each is read and locked (S012 § 3; the design of S009 § 5.1–5.2)
# ---------------------------------------------------------------------------

def _found(row):
    """The row, or a 404 when there is none."""
    if row is None:
        raise ApiError("Not found", 404)
    return row


def _read_node(cur, node_id):
    """Plain read with unit access (404 outside the user's units)."""
    _, node = load_node_for_user(cur, node_id, for_update=False)
    return node


def _read_node_for_change(cur, node_id, key):
    """Plain read: access (404), ``key`` at the node's site (403, S011) and an early scrapped
    check, so a refused or scrapped node gets no file read or written.  The decisions that
    count are the locked ones (_lock_node_for_change)."""
    _, node = load_node_for_user(cur, node_id, for_update=False, key=key)
    if node["lifecycle"] == SCRAPPED:
        raise ApiError(SCRAPPED_MESSAGE, 409)
    return node


def _lock_node_for_change(cur, node_id, key):
    """Lock the node (1), check ``key`` at its site (403, S011) and refuse a scrapped one from
    the locked row (S002 BR3-01)."""
    locked, _ = load_node_for_user(cur, node_id, for_update=True, key=key)
    if locked["lifecycle"] == SCRAPPED:
        raise ApiError(SCRAPPED_MESSAGE, 409)


def _lock_node_for_purge(cur, node_id, key):
    """Lock the node (1) with access and ``key`` at its site, but no scrapped check: erasing a
    file is disposition of information, not a change to the asset record (S008 § 5.3)."""
    load_node_for_user(cur, node_id, for_update=True, key=key)


def _read_model(cur, model_id, _key=None):
    """Plain read of the model; 404 when missing.  The route's require_perm has checked the
    key, held at any site (S012 § 5.5): a model has no site."""
    cur.execute("SELECT id, active FROM equipment_models WHERE id = %s", (model_id,))
    return _found(cur.fetchone())


def _lock_model(cur, model_id, _key=None):
    """Lock (4), on the model row alone.  No state to decide: an inactive model keeps its
    documents listed, served and editable (S012 § 5.2)."""
    cur.execute("SELECT id FROM equipment_models WHERE id = %s FOR UPDATE", (model_id,))
    _found(cur.fetchone())


@dataclass(frozen=True)
class Owner:
    column: str                    # the owner column of equipment_documents
    path: str                      # the documents collection URL; {} is the owner's id
    log_name: str                  # how log lines name it ("of node 12", "of model 3")
    read: Callable                 # (cur, id) -> row; 404 when missing or not visible
    read_for_change: Callable      # (cur, id, key) -> row; a write's early refusals, no lock
    lock_for_change: Callable      # (cur, id, key), in the write transaction; 404 / 403 / 409
    lock_for_purge: Callable       # (cur, id, key), as lock_for_change without the scrapped check
    read_key: str                  # list, file, thumb
    write_key: str                 # upload, title, remove
    purge_key: str                 # the removed list's restore and purge


OWNERS = {
    "equipment": Owner("equipment_id", "/api/equipment/{}/documents", "node",
                       _read_node, _read_node_for_change, _lock_node_for_change, _lock_node_for_purge,
                       "equipment:read", "equipment:edit", "equipment:purge_documents"),
    "model": Owner("model_id", "/api/masters/equipment-models/{}/documents", "model",
                   _read_model, _read_model, _lock_model, _lock_model,
                   "equipment:read", "equipment:edit", "equipment:purge_documents"),
    # Photos and documents (S018 user decision 5); raisers add them without equipment:edit
    "ticket": Owner("ticket_id", "/api/tickets/{}/documents", "ticket",
                    read_ticket, read_ticket_for_change, lock_ticket_for_change, lock_ticket_for_purge,
                    "ticket:read", "ticket:raise", "equipment:purge_documents"),
}

# The collection prefixes, one stacked route decorator each
_NODE_DOCS = "/equipment/<int:owner_id>/documents"
_MODEL_DOCS = "/masters/equipment-models/<int:owner_id>/documents"
_TICKET_DOCS = "/tickets/<int:owner_id>/documents"
_FOR_NODE = {"defaults": {"owner": "equipment"}}
_FOR_MODEL = {"defaults": {"owner": "model"}}
_FOR_TICKET = {"defaults": {"owner": "ticket"}}


def _owner_key(owner, which):
    """The owner's key for this operation (``read_key``, ``write_key`` or ``purge_key``),
    checked as held at any site — what the route-level require_perm did when every key was
    equipment's — and returned for the read or lock function to check at the record's site."""
    key = getattr(OWNERS[owner], which)
    check_perm(key)
    return key


def _item(row):
    """A row as the API shows it.  The stored name is internal (a path part) and never
    goes to the client."""
    item = row_to_dict({key: value for key, value in row.items() if key != "stored_name"})
    item["has_thumb"] = bool(item["has_thumb"])
    return item


def _read_item(cur, owner, owner_id, doc_id):
    """A document of this owner that is not removed, as listed; None otherwise."""
    cur.execute(f"SELECT {_ITEM_COLUMNS}, stored_name FROM equipment_documents "
                f"WHERE id = %s AND {OWNERS[owner].column} = %s AND removed_at IS NULL", (doc_id, owner_id))
    return cur.fetchone()


def _list_items(cur, owner, owner_id):
    """The owner's documents not removed, newest first."""
    cur.execute(f"SELECT {_ITEM_COLUMNS} FROM equipment_documents "
                f"WHERE {OWNERS[owner].column} = %s AND removed_at IS NULL ORDER BY created_at DESC, id DESC",
                (owner_id,))
    return [_item(row) for row in cur.fetchall()]


def _inherited(cur, node):
    """The node's model group (S012 § 5.6), left out when the model has no documents.  A node
    shows its own model's documents only, not its parent's (§ 9.6)."""
    items = _list_items(cur, "model", node["model_id"])
    if not items:
        return []
    return [{"owner": "model", "id": node["model_id"],
             "label": model_label(node["manufacturer_name"], node["model_designation"]),
             "path": OWNERS["model"].path.format(node["model_id"]), "items": items}]


# ---------------------------------------------------------------------------
# List and upload
# ---------------------------------------------------------------------------

@documents_bp.route(_NODE_DOCS, strict_slashes=False, **_FOR_NODE)
@documents_bp.route(_MODEL_DOCS, strict_slashes=False, **_FOR_MODEL)
@documents_bp.route(_TICKET_DOCS, strict_slashes=False, **_FOR_TICKET)
def list_documents(owner, owner_id):
    _owner_key(owner, "read_key")
    with get_db().cursor() as cur:
        row = OWNERS[owner].read(cur, owner_id)
        result = {"items": _list_items(cur, owner, owner_id), "upload_max_mb": upload_max_mb(cur)}
        if owner == "equipment":
            result["inherited"] = _inherited(cur, row)
        return jsonify(result)


def _read_upload(limit_mb):
    """The checks of S006 § 5.6 step 2 -> (clean form fields, file bytes, file type,
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


def _write_files(owner, owner_id, name, data, thumb):
    """S006 § 5.6 step 3, no transaction open -> the paths written.  A storage error
    removes what was written and becomes a 503."""
    written = []
    try:
        written.append(file_store.write_file(owner, owner_id, name, data))
        if thumb is not None:
            written.append(file_store.write_file(owner, owner_id, thumb_name(name), thumb))
    except OSError as exc:
        for path in written:
            file_store.remove_quietly(path)
        logger.error("File storage write failed for %s %s: %s (errno %s, %s)",
                     OWNERS[owner].log_name, owner_id, exc.filename, exc.errno, exc.strerror)
        raise ApiError(STORAGE_UNAVAILABLE, 503) from exc
    return written


@documents_bp.route(_NODE_DOCS, methods=["POST"], strict_slashes=False, **_FOR_NODE)
@documents_bp.route(_MODEL_DOCS, methods=["POST"], strict_slashes=False, **_FOR_MODEL)
@documents_bp.route(_TICKET_DOCS, methods=["POST"], strict_slashes=False, **_FOR_TICKET)
def upload_document(owner, owner_id):
    key = _owner_key(owner, "write_key")
    conn = get_db()
    # Step 1 — plain read: 404, and for a node or a ticket the write key at its site (403,
    # S011) and an early scrapped / closed check, so a refused record gets no file read or
    # written.  The decisions that count are the locked ones below.
    with conn.cursor() as cur:
        OWNERS[owner].read_for_change(cur, owner_id, key)
        limit_mb = upload_max_mb(cur)

    clean, data, file_type, thumb, original_name = _read_upload(limit_mb)   # step 2
    if clean["kind"] == "photo" and thumb is None:
        logger.warning("No thumbnail for a photo on %s %s (%s): Pillow could not read it",
                       OWNERS[owner].log_name, owner_id, original_name)
    content_type, ext = FILE_TYPES[file_type]
    name = stored_name(secrets.token_hex(STORED_TOKEN_BYTES), ext)
    written = _write_files(owner, owner_id, name, data, thumb)              # step 3

    try:                                                                    # step 4
        with transaction(conn), conn.cursor() as cur:
            # The one owner lock; 404 (access, from the locked state); 403; 409
            OWNERS[owner].lock_for_change(cur, owner_id, key)
            doc_id = insert_row(cur, "equipment_documents", {
                OWNERS[owner].column: owner_id,
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
            item = _item(_read_item(cur, owner, owner_id, doc_id))
    except BaseException:
        # Step 5 — any failure leaves no file behind; the original error is what the user gets
        for path in written:
            file_store.remove_quietly(path)
        raise

    return jsonify(item), 201


# ---------------------------------------------------------------------------
# Serving
# ---------------------------------------------------------------------------

def _serve(owner, owner_id, doc_id, thumbnail):
    _owner_key(owner, "read_key")
    with get_db().cursor() as cur:
        OWNERS[owner].read(cur, owner_id)
        doc = _read_item(cur, owner, owner_id, doc_id)
    if doc is None or (thumbnail and not doc["has_thumb"]):
        raise ApiError("Not found", 404)
    if thumbnail:
        name, content_type, ext = thumb_name(doc["stored_name"]), "image/jpeg", THUMB_EXTENSION
    else:
        name, content_type = doc["stored_name"], doc["content_type"]
        ext = name.rsplit(".", 1)[1]
    path = file_store.file_path(owner, owner_id, name)
    if not file_store.is_file(path):
        # The row is there but the file is not: the mount or the backup is wrong
        logger.error("File missing for document %s of %s %s: %s", doc_id, OWNERS[owner].log_name, owner_id, path)
        raise ApiError("File missing", 404)
    response = send_file(path, mimetype=content_type, download_name=safe_download_name(doc["title"], ext),
                         conditional=True, max_age=CACHE_MAX_AGE_S)
    response.headers["X-Content-Type-Options"] = "nosniff"
    # send_file marks a max_age response public; these files are per-user (access checked)
    response.cache_control.public = False
    response.cache_control.private = True
    return response


@documents_bp.route(f"{_NODE_DOCS}/<int:doc_id>/file", **_FOR_NODE)
@documents_bp.route(f"{_MODEL_DOCS}/<int:doc_id>/file", **_FOR_MODEL)
@documents_bp.route(f"{_TICKET_DOCS}/<int:doc_id>/file", **_FOR_TICKET)
def get_document_file(owner, owner_id, doc_id):
    return _serve(owner, owner_id, doc_id, thumbnail=False)


@documents_bp.route(f"{_NODE_DOCS}/<int:doc_id>/thumb", **_FOR_NODE)
@documents_bp.route(f"{_MODEL_DOCS}/<int:doc_id>/thumb", **_FOR_MODEL)
@documents_bp.route(f"{_TICKET_DOCS}/<int:doc_id>/thumb", **_FOR_TICKET)
def get_document_thumb(owner, owner_id, doc_id):
    return _serve(owner, owner_id, doc_id, thumbnail=True)


# ---------------------------------------------------------------------------
# Edit title, remove
# ---------------------------------------------------------------------------

def _validate_title_body(body, _creating):
    """Only the title; any other key is ignored, so the file, kind and owner never change."""
    title, message = validate_title(body.get("title"))
    return {"title": title}, ([{"field": "title", "message": message}] if message else [])


@documents_bp.route(f"{_NODE_DOCS}/<int:doc_id>", methods=["PUT"], **_FOR_NODE)
@documents_bp.route(f"{_MODEL_DOCS}/<int:doc_id>", methods=["PUT"], **_FOR_MODEL)
@documents_bp.route(f"{_TICKET_DOCS}/<int:doc_id>", methods=["PUT"], **_FOR_TICKET)
def update_document_title(owner, owner_id, doc_id):
    key = _owner_key(owner, "write_key")
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        OWNERS[owner].lock_for_change(cur, owner_id, key)   # the one owner lock; 404; 403; 409
        clean = clean_body(_validate_title_body, creating=False)
        # The SELECT decides the 404, not rowcount: MariaDB counts an unchanged row as
        # 0 affected, so saving the same title would look like a missing document.  The owner
        # lock serialises this with remove.
        if _read_item(cur, owner, owner_id, doc_id) is None:
            raise ApiError("Not found", 404)
        update_row(cur, "equipment_documents", doc_id, clean, actor())
        item = _item(_read_item(cur, owner, owner_id, doc_id))   # still under the owner lock
    return jsonify(item)


@documents_bp.route(f"{_NODE_DOCS}/<int:doc_id>", methods=["DELETE"], **_FOR_NODE)
@documents_bp.route(f"{_MODEL_DOCS}/<int:doc_id>", methods=["DELETE"], **_FOR_MODEL)
@documents_bp.route(f"{_TICKET_DOCS}/<int:doc_id>", methods=["DELETE"], **_FOR_TICKET)
def remove_document(owner, owner_id, doc_id):
    key = _owner_key(owner, "write_key")
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        OWNERS[owner].lock_for_change(cur, owner_id, key)   # the one owner lock; 404; 403; 409
        # One conditional statement: two removes at once give one 204 and one 404
        cur.execute("UPDATE equipment_documents SET removed_at = NOW(), removed_by = %s "
                    f"WHERE id = %s AND {OWNERS[owner].column} = %s AND removed_at IS NULL",
                    (actor(), doc_id, owner_id))
        if cur.rowcount == 0:
            raise ApiError("Not found", 404)
    return "", 204


# ---------------------------------------------------------------------------
# Removed documents: list, restore, delete for good (S008; model documents: S012 § 5.6)
# ---------------------------------------------------------------------------

# Every branch of the UNION ALL gives these columns, in this order.  The node branch is
# S008's query (an inner join to the node and NODE_JOINS); the model branch has no unit
# condition (model documents are visible at every site); the ticket branch is scoped by the
# ticket's own unit, as the node branch by the node's (S017 § 5.5).
_REMOVED_DOC_COLUMNS = (
    "d.id, d.kind, d.title, d.original_name, d.content_type, d.size_bytes, d.created_at,"
    " d.created_by, d.removed_at, d.removed_by"
)
_REMOVED_NODE_BRANCH = (
    f"SELECT {_REMOVED_DOC_COLUMNS}, 'equipment' AS owner, e.id AS owner_id, e.id AS equipment_id, e.code,"
    " e.name, e.level, e.lifecycle, s.code AS site_code, u.code AS unit_code, p.code AS p_code, gp.code AS gp_code,"
    " NULL AS mf_name, NULL AS m_designation, NULL AS ticket_state"
    " FROM equipment_documents d JOIN equipment e ON e.id = d.equipment_id" + NODE_JOINS
)
_REMOVED_MODEL_BRANCH = (
    f"SELECT {_REMOVED_DOC_COLUMNS}, 'model' AS owner, m.id AS owner_id, NULL AS equipment_id, NULL AS code,"
    " NULL AS name, NULL AS level, NULL AS lifecycle, NULL AS site_code, NULL AS unit_code, NULL AS p_code,"
    " NULL AS gp_code, mf.name AS mf_name, m.designation AS m_designation, NULL AS ticket_state"
    " FROM equipment_documents d JOIN equipment_models m ON m.id = d.model_id"
    " JOIN manufacturers mf ON mf.id = m.manufacturer_id"
)
_REMOVED_TICKET_BRANCH = (
    f"SELECT {_REMOVED_DOC_COLUMNS}, 'ticket' AS owner, t.id AS owner_id, NULL AS equipment_id, NULL AS code,"
    " t.serial AS name, NULL AS level, NULL AS lifecycle, s.code AS site_code, u.code AS unit_code, NULL AS p_code,"
    " NULL AS gp_code, NULL AS mf_name, NULL AS m_designation, t.state AS ticket_state"
    " FROM equipment_documents d JOIN tickets t ON t.id = d.ticket_id"
    " JOIN units u ON u.id = t.unit_id JOIN sites s ON s.id = u.site_id"
)

# Columns the item is built from, not shown as they are
_JOIN_COLUMNS = ("owner_id", "site_code", "unit_code", "p_code", "gp_code", "mf_name", "m_designation",
                 "ticket_state")


def _removed_item(row):
    """A removed-list row as the API shows it: ``owner`` and ``path`` (the owner's documents
    URL, which the card joins with the id and /restore or /purge); for a node its unit and
    path, for a model its label as ``name`` with the node fields null, for a ticket its serial
    as ``name``, its unit and its ``state`` (a closed ticket refuses restore)."""
    item = row_to_dict({key: value for key, value in row.items() if key not in _JOIN_COLUMNS})
    item["path"] = OWNERS[row["owner"]].path.format(row["owner_id"])
    if row["owner"] == "model":
        item["name"] = model_label(row["mf_name"], row["m_designation"])
        item["unit"] = item["full_path"] = None
    elif row["owner"] == "ticket":
        item["unit"] = f"{row['site_code']}.{row['unit_code']}"
        item["full_path"] = None
        item["state"] = row["ticket_state"]
    else:
        item["unit"] = f"{row['site_code']}.{row['unit_code']}"
        item["full_path"] = node_path(row)
    return item


def _removed_branches(cur, kind, q):
    """The UNION ALL's branches as ``[(sql, params)]``: the node and ticket branches scoped to
    the units where equipment:purge_documents is held (S011; a ticket by its own unit) and
    left out when there are none — not the whole list; the model branch at every site."""
    common, common_params = ["d.removed_at IS NOT NULL"], []
    if kind:
        common.append("d.kind = %s")
        common_params.append(kind)
    pattern = like_pattern(q) if q else None

    branches = []
    unit_ids = accessible_unit_ids(cur, "equipment:purge_documents")
    if unit_ids is None or unit_ids:
        conditions, params = list(common), list(common_params)
        if pattern:
            # The original name too: phone photos are IMG_2034 in both title and file name
            conditions.append("(e.code LIKE %s OR d.title LIKE %s OR d.original_name LIKE %s)")
            params.extend([pattern] * 3)
        if unit_ids is not None:
            conditions.append(f"u.id IN ({', '.join(['%s'] * len(unit_ids))})")
            params.extend(sorted(unit_ids))
        branches.append((f"{_REMOVED_NODE_BRANCH} WHERE {' AND '.join(conditions)}", params))

        conditions, params = list(common), list(common_params)
        if pattern:
            conditions.append("(t.serial LIKE %s OR d.title LIKE %s OR d.original_name LIKE %s)")
            params.extend([pattern] * 3)
        if unit_ids is not None:
            conditions.append(f"t.unit_id IN ({', '.join(['%s'] * len(unit_ids))})")
            params.extend(sorted(unit_ids))
        branches.append((f"{_REMOVED_TICKET_BRANCH} WHERE {' AND '.join(conditions)}", params))

    conditions, params = list(common), list(common_params)
    if pattern:
        conditions.append("(CONCAT(mf.name, ' ', m.designation) LIKE %s OR d.title LIKE %s OR d.original_name LIKE %s)")
        params.extend([pattern] * 3)
    branches.append((f"{_REMOVED_MODEL_BRANCH} WHERE {' AND '.join(conditions)}", params))
    return branches


@documents_bp.route("/equipment/removed-documents")
@require_perm("equipment:purge_documents")
def list_removed_documents():
    page = int_arg("page", 1, minimum=1, maximum=MAX_PAGE)
    per_page = int_arg("per_page", DEFAULT_PER_PAGE, minimum=1, maximum=MAX_PER_PAGE)
    kind = enum_arg("kind", KINDS)
    q = (request.args.get("q") or "").strip()

    with get_db().cursor() as cur:
        branches = _removed_branches(cur, kind, q)
        union = " UNION ALL ".join(f"({sql})" for sql, _ in branches)
        params = [p for _, branch_params in branches for p in branch_params]
        total = count(cur, f"SELECT COUNT(*) AS n FROM ({union}) removed", params)
        cur.execute(f"SELECT * FROM ({union}) removed ORDER BY removed_at DESC, id DESC LIMIT %s OFFSET %s",
                    [*params, per_page, (page - 1) * per_page])
        items = [_removed_item(row) for row in cur.fetchall()]
    return jsonify({"items": items, "total": total, "page": page, "per_page": per_page})


@documents_bp.route(f"{_NODE_DOCS}/<int:doc_id>/restore", methods=["POST"], **_FOR_NODE)
@documents_bp.route(f"{_MODEL_DOCS}/<int:doc_id>/restore", methods=["POST"], **_FOR_MODEL)
@documents_bp.route(f"{_TICKET_DOCS}/<int:doc_id>/restore", methods=["POST"], **_FOR_TICKET)
def restore_document(owner, owner_id, doc_id):
    key = _owner_key(owner, "purge_key")
    column = OWNERS[owner].column
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        # The one owner lock; 404; 403; a node also refuses scrapped, a ticket closed (409)
        OWNERS[owner].lock_for_change(cur, owner_id, key)
        cur.execute("SELECT id, title, kind, removed_by, removed_at FROM equipment_documents "
                    f"WHERE id = %s AND {column} = %s AND removed_at IS NOT NULL", (doc_id, owner_id))
        doc = cur.fetchone()
        if doc is None:
            raise ApiError("Not found", 404)
        # updated_at / updated_by record the last title edit, not a restore
        cur.execute("UPDATE equipment_documents SET removed_at = NULL, removed_by = NULL WHERE id = %s", (doc_id,))
        item = _item(_read_item(cur, owner, owner_id, doc_id))   # still under the owner lock
    logger.info("Document %s '%s' (%s) of %s %s restored by %s; removed by %s at %s",
                doc_id, doc["title"], doc["kind"], OWNERS[owner].log_name, owner_id, actor(), doc["removed_by"],
                doc["removed_at"])
    return jsonify(item)


def _remove_stored_files(owner, owner_id, doc):
    """Delete the file and its thumbnail, each attempted on its own -> True when every file
    is gone (or was already missing).  Logs what it finds; never raises."""
    names = [doc["stored_name"]]
    if doc["has_thumb"]:
        names.append(thumb_name(doc["stored_name"]))
    log_name = OWNERS[owner].log_name
    all_gone = True
    for name in names:
        path = file_store.file_path(owner, owner_id, name)
        try:
            if not file_store.remove_file(path):
                # The same sign _serve logs: the mount or the backup is wrong.  The outcome is fine.
                logger.warning("File already missing when deleting document %s of %s %s: %s",
                               doc["id"], log_name, owner_id, path)
        except OSError as exc:
            all_gone = False
            logger.error("Could not delete file %s of document %s, %s %s: errno %s, %s",
                         path, doc["id"], log_name, owner_id, exc.errno, exc.strerror)
    return all_gone


@documents_bp.route(f"{_NODE_DOCS}/<int:doc_id>/purge", methods=["POST"], **_FOR_NODE)
@documents_bp.route(f"{_MODEL_DOCS}/<int:doc_id>/purge", methods=["POST"], **_FOR_MODEL)
@documents_bp.route(f"{_TICKET_DOCS}/<int:doc_id>/purge", methods=["POST"], **_FOR_TICKET)
def purge_document(owner, owner_id, doc_id):
    key = _owner_key(owner, "purge_key")
    column = OWNERS[owner].column
    conn = get_db()
    # Row first, then the files (S008 § 5.3): after the commit nothing can restore the
    # document, so a file is never deleted from under a live row.
    with transaction(conn), conn.cursor() as cur:
        OWNERS[owner].lock_for_purge(cur, owner_id, key)   # the one owner lock; 404; 403
        cur.execute("SELECT id, title, kind, stored_name, has_thumb, created_by, removed_by, removed_at "
                    f"FROM equipment_documents WHERE id = %s AND {column} = %s", (doc_id, owner_id))
        doc = cur.fetchone()
        if doc is None:
            raise ApiError("Not found", 404)
        if doc["removed_at"] is None:
            raise ApiError("Remove the document first", 409)
        cur.execute(f"DELETE FROM equipment_documents WHERE id = %s AND {column} = %s", (doc_id, owner_id))
    # After the commit, so it is never logged for a rolled-back delete, and before the file
    # I/O, so it is there even if that hangs
    logger.info("Document %s '%s' (%s, %s) of %s %s deleted for good by %s; uploaded by %s, removed by %s at %s",
                doc_id, doc["title"], doc["kind"], doc["stored_name"], OWNERS[owner].log_name, owner_id, actor(),
                doc["created_by"], doc["removed_by"], doc["removed_at"])
    if not _remove_stored_files(owner, owner_id, doc):
        return jsonify({"warning": FILE_LEFT_BEHIND})
    return "", 204
