"""Central configuration — reads secrets and derives all config used by the app.

Import from here, not from secrets_app directly.

Secrets (credentials, URLs, IPs) live in secrets_app.py (gitignored; rendered by
Ansible in production). This module reads those raw values and derives the
structured config that the rest of the application consumes.
"""

import logging
import os

from auth_utils import _make_internal_url

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

# Dev = the Flask dev server (FLASK_DEBUG=1, PyCharm "Backend" run config).
# Tests set YANTRA_TESTING=1 in conftest.py before importing anything.
IS_DEV = os.environ.get("FLASK_DEBUG", "0") == "1"
IS_TESTING = os.environ.get("YANTRA_TESTING", "0") == "1"

# ---------------------------------------------------------------------------
# Secrets — secrets_app.py, or the example template in dev/test only
# ---------------------------------------------------------------------------

try:
    import secrets_app
except ImportError:
    if not (IS_DEV or IS_TESTING):
        raise RuntimeError(
            "secrets_app.py not found. Copy example_secrets_app.py to secrets_app.py and fill it in."
        )
    logger.warning("secrets_app.py not found — using example_secrets_app.py defaults (dev only)")
    import example_secrets_app as secrets_app

SECRET_KEY = secrets_app.SECRET_KEY

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DB_CONFIG = {
    "host": secrets_app.DB_HOST,
    "port": int(secrets_app.DB_PORT),
    "user": secrets_app.DB_USER,
    "password": secrets_app.DB_PASSWORD,
    "database": secrets_app.DB_NAME,
}

# ---------------------------------------------------------------------------
# Keycloak
# ---------------------------------------------------------------------------

# Raw realm URL from secrets, e.g. "https://sso.mspv.app/realms/Office.smtw.in"
KEYCLOAK_REALM_URL = secrets_app.KEYCLOAK_REALM_URL
KEYCLOAK_CLIENT_ID = secrets_app.KEYCLOAK_CLIENT_ID

# Split realm URL → base URL + realm name for frontend config
_parts = KEYCLOAK_REALM_URL.rsplit("/realms/", 1)
KEYCLOAK_URL = _parts[0]
KEYCLOAK_REALM = _parts[1] if len(_parts) > 1 else ""

# Internal URL for backend→Keycloak JWKS calls (bypasses DNS/proxy on LAN)
KEYCLOAK_INTERNAL_REALM_URL = _make_internal_url(
    KEYCLOAK_REALM_URL, getattr(secrets_app, "KEYCLOAK_HOST_IP", "")
)

# ---------------------------------------------------------------------------
# Dev auth bypass — refuses to start outside the dev server
# ---------------------------------------------------------------------------

DEV_AUTH_BYPASS = os.environ.get("DEV_AUTH_BYPASS", "0") == "1"
if DEV_AUTH_BYPASS and not IS_DEV:
    raise RuntimeError("DEV_AUTH_BYPASS=1 is only allowed with FLASK_DEBUG=1 (local dev server)")

DEV_STUB_ROLE = getattr(secrets_app, "DEV_STUB_ROLE", "admin")

# ---------------------------------------------------------------------------
# Data directory and uploads
# ---------------------------------------------------------------------------

# App-owned files (equipment documents and photos).  The env var is DATA_DIR because the
# production compose already sets DATA_DIR: /app/data (the App-FS share); tests point it
# at a temporary folder.  Must be one filesystem (no mount inside it), so os.replace
# stays atomic.  Default: <repo>/data in dev.
DATA_DIR = os.path.abspath(
    os.environ.get("DATA_DIR") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
)

# The upload_max_mb setting's maximum.  The request ceiling (Flask MAX_CONTENT_LENGTH,
# Nginx client_max_body_size 101M) is one MB above it, for the multipart overhead.
UPLOAD_MAX_MB_CEILING = 100
MB = 1024 * 1024

# ---------------------------------------------------------------------------
# Application version
# ---------------------------------------------------------------------------

# Read from the root VERSION file — the single source of truth also used by
# vite.config.js to bake __APP_VERSION__ into the frontend bundle.  The two are
# compared at runtime so an open browser tab can notice it is running an
# outdated build (see /api/version and frontend/src/stores/appVersion.js).
#
# Two locations because the file sits differently in dev and in the container:
#   dev        backend/config.py  ->  ../VERSION
#   container  /app/config.py     ->  /app/VERSION  (see Dockerfile.backend)
def _read_app_version():
    here = os.path.dirname(os.path.abspath(__file__))
    for path in (os.path.join(here, "VERSION"), os.path.join(here, "..", "VERSION")):
        try:
            with open(path, encoding="utf-8") as f:
                return f.read().strip()
        except OSError:
            continue
    # Not fatal: the app runs fine, the update toast simply never fires.
    return "unknown"


APP_VERSION = _read_app_version()
