"""Settings module — system status and app settings (app_settings reads and writes).

app_settings holds runtime-configurable values (key -> text).  Readers go through
get_setting_int, so an admin typo falls back to the default instead of breaking the
feature that reads it.  Only the keys in _APP_SETTINGS can be written through the API.
"""

import logging
import re

from flask import Blueprint, jsonify

from api_common import actor, clean_body
from auth_utils import require_perm
from config import DB_CONFIG, UPLOAD_MAX_MB_CEILING
from db_helpers import get_db, row_to_dict, transaction
from local_db import db_status

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
    cur.execute("SELECT setting_value FROM app_settings WHERE setting_key = %s", (key,))
    row = cur.fetchone()
    raw = row["setting_value"] if row else None
    text = raw.strip() if isinstance(raw, str) else ""
    if _WHOLE_NUMBER_RE.fullmatch(text) and minimum <= int(text) <= maximum:
        return int(text)
    logger.warning("Setting %s is %r, not a whole number %d-%d; using the default %d",
                   key, raw, minimum, maximum, default)
    return default


def upload_max_mb(cur):
    """The upload size limit in MB, read at request time so a change applies at once."""
    return get_setting_int(cur, UPLOAD_MAX_MB, *_APP_SETTINGS[UPLOAD_MAX_MB])


def _validate_app_settings(body, _creating):
    """A JSON integer in range — not a boolean, a float or a string, as ids are parsed.
    Keys other than the whitelisted ones are ignored."""
    clean, errors = {}, []
    for key, (_default, minimum, maximum) in _APP_SETTINGS.items():
        raw = body.get(key)
        if isinstance(raw, bool) or not isinstance(raw, int) or not minimum <= raw <= maximum:
            errors.append({"field": key, "message": f"Must be a whole number from {minimum} to {maximum}"})
        else:
            clean[key] = raw
    return clean, errors


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
    clean = clean_body(_validate_app_settings, creating=False)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        for key, value in clean.items():
            cur.execute("SELECT setting_value FROM app_settings WHERE setting_key = %s FOR UPDATE", (key,))
            row = cur.fetchone()
            cur.execute("INSERT INTO app_settings (setting_key, setting_value) VALUES (%s, %s) "
                        "ON DUPLICATE KEY UPDATE setting_value = %s", (key, str(value), str(value)))
            # app_settings has no updated_by, so this log line is the record of who changed it (A.8.15)
            logger.info("Setting %s changed by %s: %s -> %s",
                        key, actor(), row["setting_value"] if row else None, value)
    with conn.cursor() as cur:
        return jsonify({UPLOAD_MAX_MB: upload_max_mb(cur)})
