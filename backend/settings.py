"""Settings module — system status and app settings (app_settings reads and writes).

app_settings holds runtime-configurable values (key -> text).  Readers go through
get_setting_int (or get_setting_text and a check, as label_base_url), so an admin typo
falls back to the default instead of breaking the feature that reads it.  Only the keys in
_APP_SETTINGS can be written through /app; the internal networks (S013) and the label link
address (S014) have their own routes, as they are not numbers, and the escalation times
(S021) theirs, as one card with its own Save (_ESCALATION_SETTINGS).

Also the S013 read-only views: the access log and the background tasks.
"""

import logging
import re
from datetime import timedelta

from flask import Blueprint, g, jsonify, request

from access_control import INTERNAL_NETWORKS_KEY, clear_networks_cache, client_ip, read_stored_networks
from api_common import (
    DEFAULT_PER_PAGE, MAX_PAGE, MAX_PER_PAGE, ApiError, actor, clean_body, date_arg, enum_arg, int_arg,
    like_pattern,
)
from auth_utils import require_perm
from config import DB_CONFIG, UPLOAD_MAX_MB_CEILING
from db_helpers import count, get_db, row_to_dict, rows_to_list, transaction
from labels_core import normalise_base_url
from local_db import db_status
from network_core import format_networks, is_internal, parse_networks
from push_sender import enabled as push_enabled
from scheduled_tasks import SCHEDULE, is_overdue, next_run
from task_queue import last_enqueued

logger = logging.getLogger(__name__)

settings_bp = Blueprint("settings", __name__)

UPLOAD_MAX_MB = "upload_max_mb"
UPLOAD_MAX_MB_DEFAULT = 20
UPLOAD_MAX_MB_MIN = 1

# The settings the API may write: key -> (default, minimum, maximum)
_APP_SETTINGS = {
    UPLOAD_MAX_MB: (UPLOAD_MAX_MB_DEFAULT, UPLOAD_MAX_MB_MIN, UPLOAD_MAX_MB_CEILING),
}

# ASCII digits only: int() would also accept other scripts' digits
_WHOLE_NUMBER_RE = re.compile(r"-?[0-9]+")


def get_setting_int(cur, key, default, minimum, maximum):
    """The integer setting ``key``; a missing, non-integer or out-of-range value gives
    ``default`` and logs a warning."""
    raw = get_setting_text(cur, key, None)
    text = raw.strip() if isinstance(raw, str) else ""
    if _WHOLE_NUMBER_RE.fullmatch(text) and minimum <= int(text) <= maximum:
        return int(text)
    logger.warning("Setting %s is %r, not a whole number %d-%d; using the default %d",
                   key, raw, minimum, maximum, default)
    return default


def get_setting_text(cur, key, default):
    """The text setting ``key`` as stored, or ``default`` when there is no row.  Checking
    the value is the caller's job (label_base_url)."""
    cur.execute("SELECT setting_value FROM app_settings WHERE setting_key = %s", (key,))
    row = cur.fetchone()
    return row["setting_value"] if row and row["setting_value"] is not None else default


def _save_setting(cur, key, text):
    """Write ``key`` = ``text`` inside the caller's transaction, locking the row first so the
    logged old value is the one replaced.  The one place app_settings is written."""
    cur.execute("SELECT setting_value FROM app_settings WHERE setting_key = %s FOR UPDATE", (key,))
    row = cur.fetchone()
    cur.execute("INSERT INTO app_settings (setting_key, setting_value) VALUES (%s, %s) "
                "ON DUPLICATE KEY UPDATE setting_value = %s", (key, text, text))
    # app_settings has no updated_by, so this log line is the record of who changed it (A.8.15)
    logger.info("Setting %s changed by %s: %s -> %s", key, actor(), row["setting_value"] if row else None, text)


def upload_max_mb(cur):
    """The upload size limit in MB, read at request time so a change applies at once."""
    return get_setting_int(cur, UPLOAD_MAX_MB, *_APP_SETTINGS[UPLOAD_MAX_MB])


def _validate_int_settings(spec, values):
    """``spec`` is {field: (minimum, maximum)}, ``values`` a dict -> ``(clean, errors)`` keyed by
    field.  A JSON integer in range — not a boolean, a float or a string, as ids are parsed.
    Keys not in ``spec`` are ignored.  Shared by /app and /notifications (S021 BR2-02)."""
    clean, errors = {}, []
    for field, (minimum, maximum) in spec.items():
        raw = values.get(field)
        if isinstance(raw, bool) or not isinstance(raw, int) or not minimum <= raw <= maximum:
            errors.append({"field": field, "message": f"Must be a whole number from {minimum} to {maximum}"})
        else:
            clean[field] = raw
    return clean, errors


_APP_SPEC = {key: (minimum, maximum) for key, (_default, minimum, maximum) in _APP_SETTINGS.items()}


@settings_bp.route("/db-status")
@require_perm("settings:read")
def get_db_status():
    """Database reachability, server version and schema version.

    Always 200 — an unreachable database is a status to show, not an API error.
    """
    return jsonify(row_to_dict(db_status(DB_CONFIG)))


@settings_bp.route("/app")
@require_perm("settings:read")
def get_app_settings():
    with get_db().cursor() as cur:
        return jsonify({UPLOAD_MAX_MB: upload_max_mb(cur)})


@settings_bp.route("/app", methods=["PUT"])
@require_perm("settings:edit")
def put_app_settings():
    clean = clean_body(lambda body, _creating: _validate_int_settings(_APP_SPEC, body), creating=False)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        for key, value in clean.items():
            _save_setting(cur, key, str(value))
    with conn.cursor() as cur:
        return jsonify({UPLOAD_MAX_MB: upload_max_mb(cur)})


# ---------------------------------------------------------------------------
# Label link address (S014 § 3) — the address QR labels carry, whoever prints them
# ---------------------------------------------------------------------------

LABEL_BASE_URL = "label_base_url"
# In code, not a migration row: the card shows it until the first save (S014 § 6)
DEFAULT_LABEL_BASE_URL = "https://vel-yantra.mspv.app"


def label_base_url(cur):
    """The stored address, normalised; the default when none is stored, or (with a
    warning) when the stored text is no longer a valid address (edited by hand)."""
    raw = get_setting_text(cur, LABEL_BASE_URL, None)
    if raw is None:
        return DEFAULT_LABEL_BASE_URL
    url, _error = normalise_base_url(raw)
    if url is None:
        logger.warning("Setting %s is %r, not a valid label address; using the default %s",
                       LABEL_BASE_URL, raw, DEFAULT_LABEL_BASE_URL)
        return DEFAULT_LABEL_BASE_URL
    return url


def _validate_labels(body, _creating):
    url, error = normalise_base_url(body.get("base_url"))
    if error:
        return {}, [{"field": "base_url", "message": error}]
    return {"base_url": url}, []


@settings_bp.route("/labels")
@require_perm("settings:read")
def get_labels():
    with get_db().cursor() as cur:
        return jsonify({"base_url": label_base_url(cur)})


@settings_bp.route("/labels", methods=["PUT"])
@require_perm("settings:edit")
def put_labels():
    url = clean_body(_validate_labels, creating=False)["base_url"]
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        _save_setting(cur, LABEL_BASE_URL, url)
    return jsonify({"base_url": url})


# ---------------------------------------------------------------------------
# Notifications (S021 § 1.6) — escalation times per criticality grade, and whether push is set up
# ---------------------------------------------------------------------------

# Grade -> (key, default, minimum, maximum): minutes after which a breakdown nobody acknowledged
# escalates (decided 21-10-2026, Plan.MD Q2).  Its own dict, not _APP_SETTINGS: /app validates
# every key that holds (BR1-02).
_ESCALATION_SETTINGS = {
    "A": ("escalate_minutes_a", 10, 5, 1440),
    "B": ("escalate_minutes_b", 30, 5, 1440),
    "C": ("escalate_minutes_c", 60, 5, 1440),
}
_ESCALATION_SPEC = {grade: (minimum, maximum) for grade, (_key, _default, minimum, maximum)
                    in _ESCALATION_SETTINGS.items()}
ESCALATE_FIELD = "escalate_minutes"
ESCALATE_NOT_OBJECT = "Enter the three times."


def escalation_minutes(cur):
    """{"A": 10, "B": 30, "C": 60} as stored (the defaults for a missing or unreadable value),
    read when an escalation is queued, so a later change does not move one already queued."""
    return {grade: get_setting_int(cur, key, default, minimum, maximum)
            for grade, (key, default, minimum, maximum) in _ESCALATION_SETTINGS.items()}


def _validate_notifications(body, _creating):
    """``{"escalate_minutes": {"A", "B", "C"}}``: one 400 on the object when it is not one;
    otherwise each error on its box, ``escalate_minutes.A`` (BR2-02)."""
    values = body.get(ESCALATE_FIELD)
    if not isinstance(values, dict):
        return {}, [{"field": ESCALATE_FIELD, "message": ESCALATE_NOT_OBJECT}]
    clean, errors = _validate_int_settings(_ESCALATION_SPEC, values)
    return clean, [{**error, "field": f"{ESCALATE_FIELD}.{error['field']}"} for error in errors]


def _notifications_body(cur):
    return {
        ESCALATE_FIELD: escalation_minutes(cur),
        "push_enabled": push_enabled(),
        "devices": count(cur, "SELECT COUNT(*) AS n FROM push_subscriptions", ()),
    }


@settings_bp.route("/notifications")
@require_perm("settings:read")
def get_notifications():
    with get_db().cursor() as cur:
        return jsonify(_notifications_body(cur))


@settings_bp.route("/notifications", methods=["PUT"])
@require_perm("settings:edit")
def put_notifications():
    """One PUT for the whole card (§ 1.6): every value on it, saved together."""
    clean = clean_body(_validate_notifications, creating=False)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        for grade, minutes in clean.items():
            _save_setting(cur, _ESCALATION_SETTINGS[grade][0], str(minutes))
    with conn.cursor() as cur:
        return jsonify(_notifications_body(cur))


# ---------------------------------------------------------------------------
# Internal networks (S013 § 5.2)
# ---------------------------------------------------------------------------

def _network_body(networks):
    ip = client_ip()
    return {"networks": [str(n) for n in networks], "your_ip": ip, "your_ip_internal": is_internal(ip, networks)}


def _validate_networks(body, _creating):
    """{"networks": "<text>"} as typed, comma- or newline-separated -> the parsed list."""
    text = body.get("networks")
    if not isinstance(text, str):
        return {}, [{"field": "networks", "message": "Enter the ranges as text, e.g. 10.24.0.0/16"}]
    networks, error = parse_networks(text)
    if error:
        return {}, [{"field": "networks", "message": error}]
    return {"networks": networks}, []


@settings_bp.route("/network")
@require_perm("settings:read")
def get_network():
    """The stored ranges (the defaults when the stored value is unreadable) and the address
    the server sees for this request, so the editor can check what it is about to save."""
    with get_db().cursor() as cur:
        networks, _stored = read_stored_networks(cur)
    return jsonify(_network_body(networks))


@settings_bp.route("/network", methods=["PUT"])
@require_perm("settings:edit")
def put_network():
    networks = clean_body(_validate_networks, creating=False)["networks"]
    ip = client_ip()
    # The lock-out guard protects the saver only; admin may save anything (S013 § 5.2)
    if "admin" not in g.user["roles"] and not is_internal(ip, networks):
        raise ApiError(f"This would block your own address ({ip or 'unknown'}) — check every site's range "
                       "before saving", 400, "networks")
    value = format_networks(networks)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        _save_setting(cur, INTERNAL_NETWORKS_KEY, value)
    # This process at once; the other Gunicorn workers within NETWORKS_CACHE_SECONDS
    clear_networks_cache()
    return jsonify(_network_body(networks))


# ---------------------------------------------------------------------------
# Access log viewer (S013 § 5.4) — read-only: no route changes or deletes a row
# ---------------------------------------------------------------------------

_FLAG = ("0", "1")


@settings_bp.route("/access-log")
@require_perm("access_log:view")
def list_access_log():
    page = int_arg("page", 1, minimum=1, maximum=MAX_PAGE)
    per_page = int_arg("per_page", DEFAULT_PER_PAGE, minimum=1, maximum=MAX_PER_PAGE)
    user = (request.args.get("user") or "").strip()
    date_from, date_to = date_arg("from"), date_arg("to")
    external, denied = enum_arg("external", _FLAG) == "1", enum_arg("denied", _FLAG) == "1"

    where, params = [], []
    if user:
        where.append("username LIKE %s")
        params.append(like_pattern(user))
    if date_from:
        where.append("ts >= %s")
        params.append(date_from)
    if date_to:
        # `to` is inclusive: everything before the next day's midnight (IST, as ts)
        where.append("ts < %s")
        params.append(date_to + timedelta(days=1))
    if external:
        where.append("is_internal = 0")
    if denied:
        where.append("outcome <> 'ok'")
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""

    with get_db().cursor() as cur:
        total = count(cur, f"SELECT COUNT(*) AS n FROM access_log {where_sql}", params)
        cur.execute(f"SELECT id, ts, username, role, session_id, client_ip, is_internal, outcome, method, path,"
                    f" user_agent, detail FROM access_log {where_sql} ORDER BY ts DESC, id DESC LIMIT %s OFFSET %s",
                    [*params, per_page, (page - 1) * per_page])
        items = rows_to_list(cur.fetchall())
    for item in items:
        item["is_internal"] = bool(item["is_internal"])
    return jsonify({"items": items, "total": total, "page": page, "per_page": per_page})


# ---------------------------------------------------------------------------
# Background tasks (S013 § 5.6) — one line per scheduled task, and the failed count
# ---------------------------------------------------------------------------

@settings_bp.route("/tasks")
@require_perm("settings:read")
def get_tasks():
    task_types = [task_type for task_type, _ in SCHEDULE]
    with get_db().cursor() as cur:
        # The database's clock, as the worker's NOW() and the queue's timestamps (IST)
        cur.execute("SELECT NOW() AS now")
        now = cur.fetchone()["now"]
        last = last_enqueued(cur, task_types)
        lines = []
        for entry in SCHEDULE:
            cur.execute("SELECT status, created_at, completed_at FROM task_queue WHERE task_type = %s "
                        "ORDER BY id DESC LIMIT 1", (entry[0],))
            latest = cur.fetchone()
            upcoming = next_run(entry, last, now)
            lines.append({
                "task_type": entry[0],
                "daily_at": entry[1],
                "last_run": (latest["completed_at"] or latest["created_at"]) if latest else None,
                "last_status": latest["status"] if latest else None,
                "next_run": upcoming,
                "overdue": is_overdue(upcoming, now),
            })
        failed_count = count(cur, "SELECT COUNT(*) AS n FROM task_queue WHERE status = 'failed'", ())
    return jsonify({"tasks": rows_to_list(lines), "failed_count": failed_count})
