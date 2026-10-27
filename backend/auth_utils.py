"""Authentication and authorisation utilities.

- validate_keycloak_token() — decode Bearer JWT via Keycloak JWKS
- require_auth()            — before_request handler, populates g.user (no DB access)
- require_perm(key)         — route decorator, 403 unless the key is held somewhere
- check_perm(key)           — the same 403, raised inside a route whose key depends on its arguments
- has_perm(key)             — inline boolean check for field masking ("held somewhere")
- has_perm_at(key, site_id) / require_perm_at(...) — a site-scoped key at one site (S011)
- permissions_at_site(site_id) — every key the user holds at one site
- current_person_id(cur)    — the user's own person (Team record), or None (S018)
- store_login_email(...)    — copy the token's email onto the user's person (S032)
- user_unit_ids(key)        — the units where the user holds a site-scoped key
- compute_permissions(roles) — returns list of permission keys for role(s) (access_core)

Roles come from two places (S011): the token's roles (admin, it_admin, maintenance_team)
and the user's memberships in the database, one site role per site.  g.user holds only
what the token says, so serving needs no database; memberships are read lazily, once per
request and cached in g, the first time a check the token roles cannot answer needs them.
A database that is down then raises DBUnavailable (503), as the route would anyway.
"""

import functools
import json
import logging
from urllib.parse import urlparse, urlunparse

import jwt
from flask import current_app, g, jsonify, request

import access_core
from access_core import Membership, compute_permissions, expand_roles  # noqa: F401  (re-exported)
from config_rbac import LOGIN_ROLE, SITE_ROLES, SITE_SCOPED, TOKEN_ROLES
from email_core import clean_address
from masters_core import normalise_username

# api_common and db_helpers import config, which imports this module: they are imported
# inside the functions that need them (_db, require_perm_at), never at module load.


def _db():
    from db_helpers import get_db
    return get_db()

logger = logging.getLogger(__name__)

# Keycloak realm roles that map to the app-level 'admin' role.
# 'mspv-apps-admin' is the org-wide admin role in Keycloak/AD.
ADMIN_REALM_ROLES = {"admin", "mspv-apps-admin"}

# Cached PyJWKClient per JWKS URI
_jwk_clients = {}

# urllib's limit on each connect and each read of a key-list fetch, not on the whole fetch
# (a DNS lookup has none); PyJWT's default is 30 s (S059 § 1.1, CR1-02)
JWKS_TIMEOUT_S = 5

# Clock difference allowed between this server and Keycloak on exp and iat (S059 § 1.3)
TOKEN_LEEWAY_S = 30

# The answer when Keycloak's key list cannot be fetched (503, S059 § 1.2)
LOGIN_SERVER_DOWN_TEXT = "Sign-in cannot be checked right now. The login server does not answer. Try again in a minute."
# The plain texts of a 403 and a 401 (S064 UX-13): the key needed goes to the log and the access
# log (_log_denied), never to the screen
FORBIDDEN_TEXT = "You don't have permission for this. Ask your engineer or IT."
SIGN_IN_EXPIRED_TEXT = "Your sign-in has expired. Sign out, then sign in again."


class LoginServerUnavailable(Exception):
    """Keycloak's key list could not be fetched, so the token cannot be checked: an outage
    (503), not a refused token (401)."""


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
        # PyJWT refetches the key list itself for a key id it does not hold, at most once per
        # cooldown_duration (30 s): that covers key rotation, so no retry of our own (S059 § 1.1)
        _jwk_clients[jwks_uri] = jwt.PyJWKClient(jwks_uri, timeout=JWKS_TIMEOUT_S)
    return _jwk_clients[jwks_uri]


def _decode(token, jwks_url, issuer):
    """Verify the token signature against the realm's JWKS and return its payload: RS256
    only, iss equal to ``issuer``, exp, iat and iss required, TOKEN_LEEWAY_S on the times."""
    # Keycloak sets aud="account" by default, not the client_id, so we
    # skip audience verification and check azp (authorized party) instead.
    # "require" must go in options: PyJWT 2.x takes a require= keyword with only a
    # deprecation warning and ignores it (S059 § 1.3).
    decode_opts = {"verify_aud": False, "require": ["exp", "iat", "iss"]}
    try:
        signing_key = _get_jwk_client(jwks_url).get_signing_key_from_jwt(token)
    except (json.JSONDecodeError, OSError) as exc:
        # PyJWT wraps only URLError, TimeoutError and HTTPException in PyJWKClientConnectionError:
        # a 200 HTML page or a connection reset mid-body escapes as these.  Both are an outage
        # (503).  Kept this narrow so a token error (DecodeError, a PyJWTError) stays a 401 (CR1-01).
        raise jwt.exceptions.PyJWKClientConnectionError(f"key list unreadable: {exc!r}") from exc
    return jwt.decode(token, signing_key.key, algorithms=["RS256"], issuer=issuer, leeway=TOKEN_LEEWAY_S,
                      options=decode_opts)


def make_user(username, name, roles, memberships=None, stale_roles=(), session_id=None, email=""):
    """The g.user dict.  ``roles`` are token roles; ``memberships`` is None to read them
    from the database (production), or a fixed list (the dev stub and the test harness).
    ``role`` is the most privileged token role, for logging; /auth/me shows the one that
    counts the site roles too.  ``session_id`` is the token's sid claim: the Keycloak login
    session, which the access log calls a session (S013).  ``email`` is the token's email
    claim as given ("" when none); /auth/me checks it and stores it (S032 § 5.4)."""
    return {
        "username": username,
        "email": email,
        "session_id": session_id,
        "name": name,
        "role": access_core.display_role(roles, []),
        "roles": list(roles),
        "permissions": compute_permissions(list(roles)),
        "memberships": memberships,
        "stale_roles": list(stale_roles),
    }


def validate_keycloak_token(realm_url, client_id, internal_realm_url=None):
    """Extract and validate the Bearer token from the Authorization header.

    Args:
        realm_url: Public Keycloak realm URL.
        client_id: Expected client_id (checked against azp claim).
        internal_realm_url: LAN URL for fetching JWKS (if different from public).

    Returns the g.user dict (make_user) on success, or None if the token is missing or
    invalid, is not an access token, or carries none of admin, it_admin, maintenance_team.
    On None, g.access_detail holds one fixed code for the access log (S013 § 5.4): no_token,
    invalid_token, wrong_client, wrong_type or no_role — never the JWT library's message,
    which differs per probe.

    Raises LoginServerUnavailable when Keycloak's key list cannot be fetched (S059 § 1.2);
    require_auth answers it with 503 and the detail code login_server_down.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        logger.warning("Missing or malformed Authorization header")
        g.access_detail = "no_token"
        return None

    token = auth_header[7:]
    jwks_url = internal_realm_url or realm_url

    try:
        # The issuer is the public realm URL, where the browser signs in, also when the keys
        # come from the LAN address (S059 decision 5)
        payload = _decode(token, jwks_url, realm_url)
    except jwt.exceptions.PyJWKClientConnectionError as exc:
        # Before PyJWTError, its base class.  PyJWT's message carries the urllib error, not the URL.
        logger.warning("Keycloak key list not reachable at %s: %s", jwks_url, exc)
        raise LoginServerUnavailable(jwks_url) from exc
    except jwt.exceptions.PyJWTError as exc:
        logger.warning("JWT validation failed: %s", exc)
        g.access_detail = "invalid_token"
        return None

    # Verify the token was issued for this client (azp = authorized party)
    if payload.get("azp") != client_id:
        logger.warning("Token azp '%s' does not match client_id '%s'",
                       payload.get("azp"), client_id)
        g.access_detail = "wrong_client"
        return None

    # Only an access token opens the API: an ID or refresh token signed by the same realm key
    # has another typ (S059 § 1.3, RFC 8725 § 3.11).  The claim's value is logged, cut short,
    # never the token.
    if payload.get("typ") != "Bearer":
        logger.warning("Token typ %s is not Bearer", repr(payload.get("typ"))[:20])
        g.access_detail = "wrong_type"
        return None

    # Extract role — check both realm roles and client roles
    realm_roles = payload.get("realm_access", {}).get("roles", [])
    client_roles = payload.get("resource_access", {}).get(client_id, {}).get("roles", [])
    all_roles = set(realm_roles) | set(client_roles)

    # Check admin first (it's not in ROLES but bypasses everything)
    if ADMIN_REALM_ROLES & all_roles:
        matched_roles = ["admin"]
    else:
        # The token roles that grant, then the login-only role (S011 § 5.1)
        matched_roles = [r for r in TOKEN_ROLES if r in all_roles]
        if LOGIN_ROLE in all_roles:
            matched_roles.append(LOGIN_ROLE)

    if not matched_roles:
        logger.warning("No recognised role for user %s (roles: %s)",
                       payload.get("preferred_username"), sorted(all_roles))
        g.access_detail = "no_role"
        return None

    # The maintenance roles moved into Yantra (S011): old client roles are ignored, and
    # /auth/me logs who still carries them (§ 5.7 step 4)
    stale_roles = sorted(all_roles & set(SITE_ROLES))
    return make_user(payload.get("preferred_username", ""), payload.get("name", ""), matched_roles,
                     stale_roles=stale_roles, session_id=payload.get("sid"), email=payload.get("email", ""))


# ---------------------------------------------------------------------------
# Request-level auth (before_request handler)
# ---------------------------------------------------------------------------

# Paths that skip authentication
PUBLIC_PATHS = frozenset(["/api/auth/config", "/api/health", "/api/version"])


# Built lazily on first use. Cached for process lifetime — restart to
# pick up RBAC policy changes.  Set DEV_STUB_ROLE in secrets_app.py to
# test as a non-admin.  Shared by every request, so nothing per request is stored in it.
_DEV_STUB_USER = None


def _get_dev_stub_user():
    global _DEV_STUB_USER
    if _DEV_STUB_USER is None:
        import config
        role, email = config.DEV_STUB_ROLE, config.DEV_STUB_EMAIL
        if role in SITE_ROLES:
            # That role at every site, all units (S011 § 5.8)
            _DEV_STUB_USER = make_user("dev", "Dev User", [LOGIN_ROLE], [Membership(None, role, True)], email=email)
        elif role in ("admin", LOGIN_ROLE, *TOKEN_ROLES):
            # maintenance_team: a login-only stub, to see the "no access yet" page
            _DEV_STUB_USER = make_user("dev", "Dev User", [role], email=email)
        else:
            _DEV_STUB_USER = make_user("dev", "Dev User", [], [], email=email)
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

        # In test mode the X-Test-Role header sets the user through the harness's factory, here,
        # so every later hook (the network gate, the access log) sees g.user as in production
        # (S013 BR1-02).  No factory configured: refused, never let through.  X-Test-Email stands
        # for the token's email claim (S032 BR1-04), empty when absent.
        test_role = request.headers.get("X-Test-Role")
        if current_app.config.get("TESTING") and test_role:
            factory = current_app.config.get("TEST_USER_FACTORY")
            if factory is None:
                g.access_outcome = "auth_failed"
                return jsonify({"error": SIGN_IN_EXPIRED_TEXT}), 401
            g.user = factory(test_role, request.headers.get("X-Test-User"), request.headers.get("X-Test-Email", ""))
            return None

        if dev_bypass:
            g.user = _get_dev_stub_user()
            return None

        try:
            user = validate_keycloak_token(realm_url, client_id, internal_realm_url)
        except LoginServerUnavailable:
            # An outage, not a refusal of the person: auth_failed with its own detail (S059 § 1.2)
            g.access_outcome = "auth_failed"
            g.access_detail = "login_server_down"
            return jsonify({"error": LOGIN_SERVER_DOWN_TEXT}), 503
        if user is None:
            logger.warning("Auth failed for %s %s", request.method, request.path)
            g.access_outcome = "auth_failed"
            return jsonify({"error": SIGN_IN_EXPIRED_TEXT}), 401

        g.user = user
        return None  # continue to the route

    return handler


# ---------------------------------------------------------------------------
# Memberships and units — loaded lazily, once per request (g)
# ---------------------------------------------------------------------------

_NOT_LOADED = object()


def current_person_id(cur):
    """The active person whose login is the token's username, or None: no such person, or
    an inactive one, has no access (S011 A1 rule 3; a deactivated leaver loses it on the
    next request).  Cached for the request.  Public since S018: the user's own person is the
    default technician, the labour default, the auto-assignee and *Assigned to me*."""
    if g.get("_access_person_id", _NOT_LOADED) is _NOT_LOADED:
        cur.execute("SELECT id FROM people WHERE username = %s AND active = 1",
                    (normalise_username(g.user["username"]),))
        row = cur.fetchone()
        g._access_person_id = row["id"] if row else None
    return g._access_person_id


def store_login_email(cur, person_id, email):
    """Copy the login token's email onto the person (S032 § 5.4): stripped and lower-cased when
    email_core accepts it, else NULL (no claim, or a broken one, clears it) -> the UPDATE's row
    count, 0 when it was already so.  Keycloak is the one source of the address; Yantra keeps a
    copy because the worker sends without a token.  updated_at / updated_by stay as they were: a
    cached value, not an edit of the Team record."""
    address = clean_address(email)
    cur.execute("UPDATE people SET email = %s WHERE id = %s AND NOT (email <=> %s)", (address, person_id, address))
    return cur.rowcount


def current_memberships():
    """The user's memberships (a list of access_core.Membership).  Fixed ones (dev stub,
    test harness) need no query; otherwise read through the request's connection, so a
    write transaction sees the same."""
    fixed = g.user.get("memberships")
    if fixed is not None:
        return fixed
    if "_access_memberships" not in g:
        memberships = []
        with _db().cursor() as cur:
            person_id = current_person_id(cur)
            if person_id is not None:
                cur.execute("SELECT site_id, role, all_units FROM memberships WHERE person_id = %s",
                            (person_id,))
                memberships = [Membership(r["site_id"], r["role"], bool(r["all_units"]))
                               for r in cur.fetchall()]
        g._access_memberships = memberships
    return g._access_memberships


def membership_sites(memberships):
    """[{site_id, site_code, role, all_units}] for /auth/me, by site code.  A membership that
    is not a site role grants nothing and is left out; a wildcard one (dev stub, tests) is
    shown with site_id and site_code null."""
    valid = access_core.valid_memberships(memberships)
    site_ids = sorted({m.site_id for m in valid if m.site_id is not None})
    codes = {}
    if site_ids:
        with _db().cursor() as cur:
            cur.execute(f"SELECT id, code FROM sites WHERE id IN ({', '.join(['%s'] * len(site_ids))})", site_ids)
            codes = {r["id"]: r["code"] for r in cur.fetchall()}
    sites = [{"site_id": m.site_id, "site_code": codes.get(m.site_id), "role": m.role, "all_units": m.all_units}
             for m in valid]
    return sorted(sites, key=lambda s: s["site_code"] or "")


def _cached_memberships():
    """What is known without a query, for log lines."""
    fixed = g.user.get("memberships")
    return fixed if fixed is not None else g.get("_access_memberships", [])


def logged_role(user):
    """The display role from what is known without a query (the token roles and any
    memberships already read this request), for the access log (S013 § 4)."""
    return access_core.display_role(user.get("roles", []), _cached_memberships())


def _unit_pools(memberships):
    """(active units, the user's own active unit rows), both as (unit_id, site_id).  Every
    active unit is read only when some valid membership has all units."""
    if "_access_units" not in g:
        valid = access_core.valid_memberships(memberships)
        units, own = [], []
        if valid:
            with _db().cursor() as cur:
                if any(m.all_units for m in valid):
                    cur.execute("SELECT id, site_id FROM units WHERE active = 1")
                    units = [(r["id"], r["site_id"]) for r in cur.fetchall()]
                person_id = current_person_id(cur)
                if person_id is not None:
                    cur.execute("SELECT pu.unit_id, u.site_id FROM person_units pu JOIN units u ON u.id = pu.unit_id "
                                "WHERE pu.person_id = %s AND u.active = 1", (person_id,))
                    own = [(r["unit_id"], r["site_id"]) for r in cur.fetchall()]
        g._access_units = (units, own)
    return g._access_units


# ---------------------------------------------------------------------------
# Permission helpers
# ---------------------------------------------------------------------------

def _is_admin(user):
    return "admin" in user.get("roles", ())


def has_perm(perm_key):
    """Check if the current user (g.user) holds the given permission somewhere: from a
    token role (no query), or from a site role at any site.
    Use inside a route for conditional field masking.
    """
    user = getattr(g, "user", None)
    if user is None:
        return False
    if _is_admin(user) or perm_key in user.get("permissions", []):
        return True
    return perm_key in access_core.global_permissions(user["roles"], current_memberships())


def global_permissions():
    """Every key the user holds somewhere (navigation, /auth/me)."""
    return access_core.global_permissions(g.user["roles"], current_memberships())


def _check_site_args(perm_key, site_id):
    # Programming errors, seen in tests: a global key checked at a site, or a new site key
    # missing from SITE_SCOPED, or a site that was never resolved
    assert perm_key in SITE_SCOPED, f"{perm_key} is not in SITE_SCOPED"
    assert isinstance(site_id, int) and not isinstance(site_id, bool), f"site_id {site_id!r} is not an id"


def has_perm_at(perm_key, site_id):
    """The site-scoped key at one site: admin, a token role grants it, or the role held at
    that site does."""
    _check_site_args(perm_key, site_id)
    user = getattr(g, "user", None)
    if user is None:
        return False
    if _is_admin(user) or perm_key in user.get("permissions", []):
        return True
    return access_core.has_key_at(perm_key, user["roles"], current_memberships(), site_id)


def require_perm_at(perm_key, site_id, field=None):
    """Raise a 403 naming the site unless the user holds the key there.  The site code
    comes from a plain read of sites, never from a locking read."""
    from api_common import ApiError
    if has_perm_at(perm_key, site_id):
        return
    with _db().cursor() as cur:
        cur.execute("SELECT code FROM sites WHERE id = %s", (site_id,))
        row = cur.fetchone()
    logger.warning("Permission denied: %s requires '%s' at site %s (user=%s)",
                   request.path, perm_key, site_id, g.user.get("username", "?"))
    g.access_outcome, g.access_detail = "denied_perm", f"{perm_key}@site:{site_id}"
    raise ApiError(f"You can't do this at {row['code'] if row else 'this site'}", 403, field)


def permissions_at_site(site_id):
    """The user's full key list at one site: the token keys and the site role's (every key
    for admin).  The node detail sends it, so screens follow the node's site."""
    user = g.user
    if _is_admin(user):
        return compute_permissions(["admin"])
    return access_core.permissions_at(user["roles"], current_memberships(), site_id)


def user_unit_ids(perm_key):
    """None = every unit; otherwise the set of active unit ids where the user holds the
    site-scoped key (access_core.unit_ids_for).  An empty set is no access, not an error."""
    assert perm_key in SITE_SCOPED, f"{perm_key} is not in SITE_SCOPED"
    user = g.user
    if access_core.every_unit_by_token(perm_key, user["roles"]):
        return None   # no query needed
    memberships = current_memberships()
    units, own = _unit_pools(memberships)
    return access_core.unit_ids_for(perm_key, user["roles"], memberships, units, own)


def _log_denied(perm_key):
    user = getattr(g, "user", None) or {}
    role = access_core.display_role(user.get("roles", []), _cached_memberships()) if user else "?"
    logger.warning("Permission denied: %s requires '%s' (user=%s, role=%s)",
                   request.path, perm_key, user.get("username", "?"), role)
    g.access_outcome, g.access_detail = "denied_perm", perm_key


def require_perm(perm_key):
    """Route decorator — returns 403 if the user lacks the permission everywhere.
    Place immediately after @bp.route().  Site-scoped keys are checked again at the
    record's site (has_perm_at), where the site is known.
    """
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            if not has_perm(perm_key):
                _log_denied(perm_key)
                return jsonify({"error": FORBIDDEN_TEXT}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def check_perm(perm_key):
    """require_perm inside a route, for a key that depends on the route's arguments
    (documents.py: each owner names its keys, S017 § 5.5): the same 403, raised."""
    from api_common import ApiError
    if not has_perm(perm_key):
        _log_denied(perm_key)
        raise ApiError(FORBIDDEN_TEXT, 403)
