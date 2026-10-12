"""Settings module — system status and app settings."""

from flask import Blueprint, jsonify

from auth_utils import require_perm
from config import DB_CONFIG
from db_helpers import row_to_dict
from local_db import db_status

settings_bp = Blueprint("settings", __name__)


@settings_bp.route("/db-status")
@require_perm("settings:read")
def get_db_status():
    """Database reachability, server version and schema version.

    Always 200 — an unreachable database is a status to show, not an API error.
    """
    return jsonify(row_to_dict(db_status(DB_CONFIG)))
