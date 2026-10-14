"""Flask application entry point — blueprint registration and startup."""

import logging
import os
import time

from flask import Flask, g, jsonify, request
from flask_cors import CORS

from auth_utils import require_auth
from config import (
    APP_VERSION, DB_CONFIG, DEV_AUTH_BYPASS, KEYCLOAK_CLIENT_ID,
    KEYCLOAK_INTERNAL_REALM_URL, KEYCLOAK_REALM, KEYCLOAK_REALM_URL, KEYCLOAK_URL,
    SECRET_KEY,
)
from db_helpers import close_db
from local_db import DBUnavailable, ensure_schema, init_pool

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Database — pool opens lazily; migrations are tried now and retried later,
# so the app starts even while the database does not exist yet.
# ---------------------------------------------------------------------------

init_pool(DB_CONFIG, maxconn=10)
ensure_schema(DB_CONFIG)

app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY
CORS(app, origins=os.environ.get("CORS_ORIGINS", "http://localhost:5176").split(","))


# ---------------------------------------------------------------------------
# Auth middleware — validates Bearer token and populates g.user
# ---------------------------------------------------------------------------

app.before_request(require_auth(
    KEYCLOAK_REALM_URL, KEYCLOAK_CLIENT_ID, KEYCLOAK_INTERNAL_REALM_URL,
    dev_bypass=DEV_AUTH_BYPASS,
))


app.teardown_appcontext(close_db)


@app.errorhandler(DBUnavailable)
def _db_unavailable(exc):
    return jsonify({"error": f"Database unavailable: {exc}"}), 503


# ---------------------------------------------------------------------------
# Slow-request logger — flags any request exceeding SLOW_REQUEST_MS
# ---------------------------------------------------------------------------

SLOW_REQUEST_MS = int(os.environ.get("SLOW_REQUEST_MS", "3000"))
_req_logger = logging.getLogger("slow_request")


@app.before_request
def _start_request_timer():
    g._req_start = time.monotonic()


@app.after_request
def _log_slow_request(response):
    start = getattr(g, "_req_start", None)
    if start is None:
        return response
    elapsed_ms = int((time.monotonic() - start) * 1000)
    if elapsed_ms >= SLOW_REQUEST_MS:
        _req_logger.warning("SLOW %d ms  %s %s  status=%s",
                            elapsed_ms, request.method, request.path, response.status_code)
    return response


# ---------------------------------------------------------------------------
# Core routes
# ---------------------------------------------------------------------------

@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/api/version")
def version():
    """Return the deployed application version.

    Public and deliberately cheap — no DB access.  The frontend polls this and
    compares it against the version baked into its own bundle; a mismatch
    prompts the user to reload.
    """
    return jsonify({"version": APP_VERSION})


@app.route("/api/auth/config")
def auth_config():
    """Return Keycloak configuration for frontend initialisation."""
    return jsonify({
        "url": KEYCLOAK_URL,
        "realm": KEYCLOAK_REALM,
        "clientId": KEYCLOAK_CLIENT_ID,
        "devBypass": DEV_AUTH_BYPASS,
    })


@app.route("/api/auth/me")
def auth_me():
    """Return the current user's profile and permissions."""
    return jsonify({
        "username": g.user["username"],
        "name": g.user["name"],
        "role": g.user["role"],
        "roles": g.user["roles"],
        "permissions": g.user["permissions"],
    })


# ---------------------------------------------------------------------------
# Blueprints
# ---------------------------------------------------------------------------

from masters import masters_bp
app.register_blueprint(masters_bp, url_prefix="/api/masters")

from settings import settings_bp
app.register_blueprint(settings_bp, url_prefix="/api/settings")


# ---------------------------------------------------------------------------
# Run (development only — use Gunicorn in production)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=5001, debug=debug)
