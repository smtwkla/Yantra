"""Flask application entry point — blueprint registration and startup."""

import logging
import os
import time

from flask import Flask, g, jsonify, request

from access_control import client_network, make_access_log_hook, require_network
from api_common import DB_LOST_TEXT, register_error_handlers
from access_core import display_role
from auth_utils import (
    current_memberships, current_person_id, global_permissions, membership_sites, require_auth, store_login_email,
)
from config import (
    APP_VERSION, DB_CONFIG, DEV_AUTH_BYPASS, KEYCLOAK_CLIENT_ID,
    KEYCLOAK_INTERNAL_REALM_URL, KEYCLOAK_REALM, KEYCLOAK_REALM_URL, KEYCLOAK_URL, MB,
    SECRET_KEY, UPLOAD_MAX_MB_CEILING,
)
from db_helpers import close_db, get_db
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
# The request ceiling: the upload setting's maximum plus one MB for the multipart overhead,
# matching Nginx's client_max_body_size 101M (S006 § 5.2)
app.config["MAX_CONTENT_LENGTH"] = (UPLOAD_MAX_MB_CEILING + 1) * MB

# The access log (S013 § 5.4) is the first after_request hook registered, above any later
# one: Flask runs them in reverse, so this one runs last and sees the final status, error
# handlers' and 500s included.  No CORS: the app is same-origin (Nginx; Vite's proxy in dev).
app.after_request(make_access_log_hook(dev_bypass=DEV_AUTH_BYPASS))


# ---------------------------------------------------------------------------
# Auth middleware — validates Bearer token and populates g.user; then the network gate
# (S013 § 5.3), which needs g.user.  Order: require_auth -> require_network -> timer.
# ---------------------------------------------------------------------------

app.before_request(require_auth(
    KEYCLOAK_REALM_URL, KEYCLOAK_CLIENT_ID, KEYCLOAK_INTERNAL_REALM_URL,
    dev_bypass=DEV_AUTH_BYPASS,
))
app.before_request(require_network(dev_bypass=DEV_AUTH_BYPASS))


app.teardown_appcontext(close_db)

# ApiError -> {error, field?}; a duplicate key -> 409 (api_common.py), for every blueprint
register_error_handlers(app)


@app.errorhandler(DBUnavailable)
def _db_unavailable(exc):
    # The cause goes to the log; the screen gets the one plain text of both 503s (S064 UX-13 row 2)
    logger.error("Database unavailable on %s %s: %s", request.method, request.path, exc)
    return jsonify({"error": DB_LOST_TEXT}), 503


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
    """Public: always 200, and whether the schema is up to date (S025 § 1.1) — the deploy
    waits for schema_ready.  ensure_schema retries the migrations itself (at most every 30 s),
    so the answer is this worker's fresh view, not a flag set once at boot.  No version or
    error text: the reason stays behind settings:read (Settings › Database)."""
    return jsonify({"status": "ok", "schema_ready": ensure_schema(DB_CONFIG) is None})


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
    """Return the current user's profile, permissions and site roles (S011 § 6).

    Called once per page load, the de-facto login: it logs the stale Keycloak maintenance
    roles a token still carries (S011 § 5.1), and answers while the database is down with
    the token's permissions only, so IT admin can still reach Settings › Database.  ``network``
    is the address the server saw and whether it counts as internal (S013 § 6).  ``person_id``
    is the user's own Team record, or null (S018 § 3: *Assigned to me*, the labour default).

    S032 § 5.4: the token's email is copied onto the person here, a GET that writes on purpose
    (this is the login moment); a no-op write on every load after the first.  No person, or the
    database down: nothing is written."""
    user = g.user
    if user["stale_roles"]:
        logger.warning("User %s still carries old Keycloak roles %s; they are ignored (S011 § 5.7)",
                       user["username"], ",".join(user["stale_roles"]))
    ip, internal = client_network()
    body = {"username": user["username"], "name": user["name"], "roles": user["roles"],
            "network": {"ip": ip, "internal": internal}}
    try:
        memberships = current_memberships()
        # Pool connections are autocommit: the one-row UPDATE commits by itself, in its own
        # short transaction (S032 § 5.6)
        with get_db().cursor() as cur:
            person_id = current_person_id(cur)
            if person_id is not None:
                store_login_email(cur, person_id, user["email"])
        body.update(role=display_role(user["roles"], memberships), permissions=global_permissions(),
                    sites=membership_sites(memberships), person_id=person_id, db_unavailable=False)
    except DBUnavailable:
        body.update(role=display_role(user["roles"], []), permissions=user["permissions"], sites=None,
                    person_id=None, db_unavailable=True)
    return jsonify(body)


# ---------------------------------------------------------------------------
# Blueprints
# ---------------------------------------------------------------------------

from equipment import equipment_bp
app.register_blueprint(equipment_bp, url_prefix="/api/equipment")

from documents import documents_bp
# Its routes spell out /equipment/..., /masters/equipment-models/... and /tickets/<id>/documents
# and /improvements/actions/<id>/documents (four owners, S012, S017, S070); Flask matches the longer rule, so no clash with tickets_bp
app.register_blueprint(documents_bp, url_prefix="/api")

from meters import meters_bp
# Node meters under /equipment/<id>/meters (S038), beside equipment_bp as documents_bp is
app.register_blueprint(meters_bp, url_prefix="/api")

from item_properties import item_properties_bp
# An item's own property values under /equipment/<id>/properties (S044), as meters_bp
app.register_blueprint(item_properties_bp, url_prefix="/api")

from tickets import tickets_bp
app.register_blueprint(tickets_bp, url_prefix="/api/tickets")

from improvements import improvements_bp
# The improvement record (S067): its own blueprint, beside the tickets it is started from
app.register_blueprint(improvements_bp, url_prefix="/api/improvements")

from masters import masters_bp
app.register_blueprint(masters_bp, url_prefix="/api/masters")

from properties import properties_bp
# The property master and its class links and model values (S043), beside the masters
app.register_blueprint(properties_bp, url_prefix="/api/masters")

from settings import settings_bp
app.register_blueprint(settings_bp, url_prefix="/api/settings")

from push import push_bp
app.register_blueprint(push_bp, url_prefix="/api/push")


# ---------------------------------------------------------------------------
# Run (development only — use Gunicorn in production)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=5001, debug=debug)
