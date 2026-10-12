"""Masters module — machine register, locations, codes (docs/Plan.MD § 4.1).

Skeleton: the blueprint and its permission gate exist; the masters arrive
module by module.
"""

from flask import Blueprint, jsonify

from auth_utils import require_perm

masters_bp = Blueprint("masters", __name__)


@masters_bp.route("/")
@require_perm("masters:read")
def list_masters():
    """List the master data types available — none yet."""
    return jsonify({"items": []})
