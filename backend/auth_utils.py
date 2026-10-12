"""Authentication and authorisation utilities.

- validate_keycloak_token() — decode Bearer JWT via Keycloak JWKS
- require_auth()            — before_request handler, populates g.user
- require_perm(key)         — route decorator, 403 if check fails
- has_perm(key)             — inline boolean check for field masking
- compute_permissions(roles) — returns list of permission keys for role(s)
"""

import functools
import logging
from urllib.parse import urlparse, urlunparse

import jwt
from flask import current_app, g, jsonify, request

from config_rbac import PERMISSIONS, ROLES, ROLE_INCLUDES

logger = logging.getLogger(__name__)

# Keycloak realm roles that map to the app-level 'admin' role.
# 'mspv-apps-admin' is the org-wide admin role in Keycloak/AD.
ADMIN_REALM_ROLES = {"admin", "mspv-apps-admin"}

# Cached PyJWKClient per JWKS URI
_jwk_clients = {}


def _make_internal_url(realm_url, host_ip):
    """Replace the hostname in a Keycloak realm URL with a LAN IP for
    server-to-server calls, switching to plain HTTP on port 8080.

    Example: https://sso.mspv.app/realms/Office → http://10.24.0.18:8080/realms/Office

    The public HTTPS cert is issued for the domain name, not the LAN IP, so
    we must use HTTP when calling via IP.  Keycloak listens on 8080 (HTTP)
    behind the reverse proxy.
    Returns the original URL if host_ip is empty.
    """
    if not host_ip:
        return realm_url
    parsed = urlparse(realm_url)
    internal = parsed._replace(scheme="http", netloc=f"{host_ip}:8080")
    return urlunparse(internal)


# ---------------------------------------------------------------------------
# Token validation
# ---------------------------------------------------------------------------

def _get_jwk_client(realm_url):
    """Return a cached PyJWKClient for the given realm URL."""
    jwks_uri = f"{realm_url}/protocol/openid-connect/certs"
    if jwks_uri not in _jwk_clients:
        _jwk_clients[jwks_uri] = jwt.PyJWKClient(jwks_uri)
    return _jwk_clients[jwks_uri]


def _decode(token, jwks_url):
    """Verify the token signature against the realm's JWKS and return its payload."""
    # Keycloak sets aud="account" by default, not the client_id, so we
    # skip audience verification and check azp (authorized party) instead.
    decode_opts = {"verify_exp": True, "verify_aud": False}
    signing_key = _get_jwk_client(jwks_url).get_signing_key_from_jwt(token)
    return jwt.decode(token, signing_key.key, algorithms=["RS256"], options=decode_opts)


def validate_keycloak_token(realm_url, client_id, internal_realm_url=None):
    """Extract and validate the Bearer token from the Authorization header.

    Args:
        realm_url: Public Keycloak realm URL.
        client_id: Expected client_id (checked against azp claim).
        internal_realm_url: LAN URL for fetching JWKS (if different from public).

    Returns a dict with 'username', 'name', 'role', 'roles' and 'permissions'
    on success, or None if the token is missing or invalid.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        logger.warning("Missing or malformed Authorization header")
        return None

    token = auth_header[7:]
    jwks_url = internal_realm_url or realm_url

    try:
        payload = _decode(token, jwks_url)
    except jwt.exceptions.PyJWTError as exc:
        logger.warning("JWT validation failed: %s", exc)
        # Retry once with fresh JWKS in case keys were rotated
        _jwk_clients.pop(f"{jwks_url}/protocol/openid-connect/certs", None)
        try:
            payload = _decode(token, jwks_url)
        except jwt.exceptions.PyJWTError as exc:
            logger.warning("JWT validation failed after JWKS refresh: %s", exc)
            return None

    # Verify the token was issued for this client (azp = authorized party)
    if payload.get("azp") != client_id:
        logger.warning("Token azp '%s' does not match client_id '%s'",
                       payload.get("azp"), client_id)
        return None

    # Extract role — check both realm roles and client roles
    realm_roles = payload.get("realm_access", {}).get("roles", [])
    client_roles = payload.get("resource_access", {}).get(client_id, {}).get("roles", [])
    all_roles = set(realm_roles) | set(client_roles)

    # Check admin first (it's not in ROLES but bypasses everything)
    if ADMIN_REALM_ROLES & all_roles:
        matched_roles = ["admin"]
    else:
        # Collect ALL matching roles (ordered most → least privileged)
        matched_roles = [r for r in ROLES if r in all_roles]

    if not matched_roles:
        logger.warning("No recognised role for user %s (roles: %s)",
                       payload.get("preferred_username"), sorted(all_roles))
        return None

    return {
        "username": payload.get("preferred_username", ""),
        "name": payload.get("name", ""),
        "role": matched_roles[0],  # primary (most privileged) for display/logging
        "roles": matched_roles,
        "permissions": compute_permissions(matched_roles),
    }


# ---------------------------------------------------------------------------
# Request-level auth (before_request handler)
# ---------------------------------------------------------------------------

# Paths that skip authentication
PUBLIC_PATHS = frozenset(["/api/auth/config", "/api/health", "/api/version"])


# Built lazily on first use. Cached for process lifetime — restart to
# pick up RBAC policy changes.  Set DEV_STUB_ROLE in secrets_app.py to
# test as a non-admin.
_DEV_STUB_USER = None


def _get_dev_stub_user():
    global _DEV_STUB_USER
    if _DEV_STUB_USER is None:
        import config
        role = config.DEV_STUB_ROLE
        _DEV_STUB_USER = {
            "username": "dev",
            "name": "Dev User",
            "role": role,
            "roles": [role],
            "permissions": compute_permissions([role]),
        }
    return _DEV_STUB_USER


def require_auth(realm_url, client_id, internal_realm_url=None, dev_bypass=False):
    """Factory that returns a before_request handler.
    Validates the Bearer token and populates g.user.

    Args:
        realm_url: Public Keycloak realm URL.
        client_id: Expected client_id.
        internal_realm_url: LAN URL for JWKS fetch (optional).
        dev_bypass: If True, skip JWT validation and use a stub user.
    """
    if dev_bypass:
        logger.warning("Auth bypass ENABLED — all requests use the dev stub user")

    def handler():
        if request.path in PUBLIC_PATHS:
            return None  # allow through

        # In test mode, allow X-Test-Role header to inject user context
        if current_app.config.get("TESTING") and request.headers.get("X-Test-Role"):
            return None  # conftest before_request will populate g.user

        if dev_bypass:
            g.user = _get_dev_stub_user()
            return None

        user = validate_keycloak_token(realm_url, client_id, internal_realm_url)
        if user is None:
            logger.warning("Auth failed for %s %s", request.method, request.path)
            return jsonify({"error": "Unauthorized"}), 401

        g.user = user
        return None  # continue to the route

    return handler


# ---------------------------------------------------------------------------
# Permission helpers
# ---------------------------------------------------------------------------

def expand_roles(roles):
    """Expand a list of roles by following ROLE_INCLUDES transitively.

    E.g. ['maint_engineer'] → {'maint_engineer', 'maint_technician', 'maint_operator'}.
    """
    expanded = set(roles)
    queue = list(roles)
    while queue:
        role = queue.pop()
        for included in ROLE_INCLUDES.get(role, ()):
            if included not in expanded:
                expanded.add(included)
                queue.append(included)
    return expanded


def compute_permissions(roles):
    """Return the sorted list of permission keys granted to any of the given roles.

    Roles are expanded via ROLE_INCLUDES before checking permissions.
    """
    if isinstance(roles, str):
        roles = [roles]
    if "admin" in roles:
        return sorted(PERMISSIONS.keys())

    effective = expand_roles(roles)

    perms = set()
    for key, granted_roles in PERMISSIONS.items():
        if granted_roles == ("*",) and any(r in ROLES for r in effective):
            perms.add(key)
        elif any(r in granted_roles for r in effective):
            perms.add(key)
    return sorted(perms)


def has_perm(perm_key):
    """Check if the current user (g.user) holds the given permission.
    Use inside a route for conditional field masking.
    """
    user = getattr(g, "user", None)
    if user is None:
        return False

    if "admin" in user.get("roles", ()):
        return True

    return perm_key in user.get("permissions", [])


def require_perm(perm_key):
    """Route decorator — returns 403 if the user lacks the permission.
    Place immediately after @bp.route().
    """
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            if not has_perm(perm_key):
                user = getattr(g, "user", None) or {}
                logger.warning("Permission denied: %s requires '%s' (user=%s, role=%s)",
                               request.path, perm_key,
                               user.get("username", "?"), user.get("role", "?"))
                return jsonify({"error": f"Forbidden: requires '{perm_key}'"}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator
