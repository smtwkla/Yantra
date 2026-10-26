"""Network gate and access log — the shell (S013 § 5; base pattern § Internet Exposure).

- client_network()        — the client address (X-Real-IP) and whether it is internal, once per request
- internal_networks()     — the internal ranges from app_settings, cached per process, with fallbacks
- require_network(...)    — before_request factory: refuses IT admin from outside (after require_auth)
- make_access_log_hook()  — after_request factory: one access_log row per sighting per day

The decisions are pure (network_core.py); this module reads the request, the settings
table and writes the log.  Neither hook may lock the plant out or break a request: the gate
reads no database beyond the cached ranges, and the log write is skipped while the
database is down.
"""

import logging
import time

import pymysql
from flask import g, jsonify, request

from auth_utils import PUBLIC_PATHS, logged_role
from company_settings import NETWORKS_CACHE_SECONDS, SIGHTING_WINDOW_MINUTES
from config import DB_CONFIG, IS_DEV
from db_helpers import get_db
from local_db import DBUnavailable, ensure_schema, get_pooled_db, return_pooled_db
from network_core import (
    DEFAULT_INTERNAL_NETWORKS, OUTCOMES, SightingCache, classify_outcome, gate_refuses, is_internal, parse_ip,
    parse_networks, sighting_hash, truncate,
)

logger = logging.getLogger(__name__)

INTERNAL_NETWORKS_KEY = "internal_networks"

NETWORK_DENIED_MESSAGE = "Yantra can be used from the plant network only for your role"

# In dev (no Nginx) a missing X-Real-IP falls back to the socket address, so the dev server
# works on localhost.  Production always has X-Real-IP from Nginx; the tests turn it off.
REMOTE_ADDR_FALLBACK = IS_DEV

# After a failure, how long the ranges loader and the log writer leave the database alone,
# as ensure_schema does (S013 § 5.2, § 5.4)
DB_BACKOFF_SECONDS = 30

# access_log column widths (migration v10)
_IP_CHARS = 45
_METHOD_CHARS = 10
_TEXT_CHARS = 255
_NAME_CHARS = 100


# ---------------------------------------------------------------------------
# Client address
# ---------------------------------------------------------------------------

def client_ip():
    """The address Nginx vouches for, from X-Real-IP only — never X-Forwarded-For, whose
    first entry is whatever the client sent.  Missing gives "" (external)."""
    raw = request.headers.get("X-Real-IP")
    if raw is None and REMOTE_ADDR_FALLBACK:
        return request.remote_addr or ""
    return (raw or "").strip()


def client_network():
    """(ip, internal) for this request, worked out once and kept on g."""
    if "_client_network" not in g:
        ip = client_ip()
        g._client_network = (ip, is_internal(ip, internal_networks()))
    return g._client_network


# ---------------------------------------------------------------------------
# Internal networks — app_settings, cached per process
# ---------------------------------------------------------------------------

_DEFAULT_NETWORKS = parse_networks(DEFAULT_INTERNAL_NETWORKS)[0]

_networks = None          # the last list read, or None before the first read
_networks_read_at = 0.0
_networks_retry_at = 0.0  # while the database is down: the next time to try


def clear_networks_cache():
    """Forget the cached ranges, so the next request reads them (after a save; tests)."""
    global _networks, _networks_read_at, _networks_retry_at
    _networks, _networks_read_at, _networks_retry_at = None, 0.0, 0.0


def read_stored_networks(cur):
    """(networks, stored text) from app_settings.  A missing or unreadable value is logged
    and gives the defaults, so a hand-edit can't lock the plant out."""
    cur.execute("SELECT setting_value FROM app_settings WHERE setting_key = %s", (INTERNAL_NETWORKS_KEY,))
    row = cur.fetchone()
    stored = row["setting_value"] if row else None
    networks, error = parse_networks(stored)
    if error:
        logger.warning("Setting %s is %r (%s); using the defaults %s",
                       INTERNAL_NETWORKS_KEY, stored, error, DEFAULT_INTERNAL_NETWORKS)
        return _DEFAULT_NETWORKS, stored
    return networks, stored


def internal_networks():
    """The internal ranges, read through a NETWORKS_CACHE_SECONDS cache per process.  While
    the database is unreachable: the last list read, else the defaults (never fail closed:
    IT admin must reach Settings › Database in an outage; S013 BR1-01)."""
    global _networks, _networks_read_at, _networks_retry_at
    now = time.monotonic()
    if _networks is not None and now - _networks_read_at < NETWORKS_CACHE_SECONDS:
        return _networks
    if now < _networks_retry_at:
        return _networks if _networks is not None else _DEFAULT_NETWORKS
    try:
        with get_db().cursor() as cur:
            networks, _stored = read_stored_networks(cur)
    except (DBUnavailable, pymysql.MySQLError) as exc:
        _networks_retry_at = now + DB_BACKOFF_SECONDS
        logger.warning("Internal networks unreadable (%s); using the %s list", exc,
                       "cached" if _networks is not None else "default")
        return _networks if _networks is not None else _DEFAULT_NETWORKS
    _networks, _networks_read_at = networks, now
    return networks


# ---------------------------------------------------------------------------
# The network gate
# ---------------------------------------------------------------------------

def _skipped(dev_bypass):
    return dev_bypass or request.method == "OPTIONS" or request.path in PUBLIC_PATHS


def require_network(dev_bypass=False):
    """Factory for the before_request gate, registered after require_auth (it needs g.user;
    Flask stops at a 401, so it never runs then).  Refuses an external request from a user
    holding a role in INTERNAL_ONLY_ROLES, from the token roles alone: no membership read,
    so it behaves the same while the database is down.  Admin, public paths, OPTIONS and the
    dev bypass pass."""

    def handler():
        if _skipped(dev_bypass):
            return None
        user = g.get("user")
        if user is None or "admin" in user["roles"]:
            return None
        ip, internal = client_network()
        if not gate_refuses(user["roles"], internal):
            return None
        g.access_outcome = "denied_network"
        logger.warning("Network gate: %s (roles %s) refused from external address %r on %s %s",
                       user["username"], ",".join(user["roles"]), ip, request.method, request.path)
        return jsonify({"error": NETWORK_DENIED_MESSAGE, "code": "network_denied", "ip": ip}), 403

    return handler


# ---------------------------------------------------------------------------
# The access log
# ---------------------------------------------------------------------------

_sightings = SightingCache(SIGHTING_WINDOW_MINUTES * 60)
_log_backoff_until = 0.0


def reset_access_log_state():
    """Forget the sightings and any back-off (tests)."""
    global _log_backoff_until
    _sightings.clear()
    _log_backoff_until = 0.0


def _error_text(response):
    """The {error} message of a JSON refusal, else None."""
    if not response.is_json:
        return None
    body = response.get_json(silent=True)
    return body.get("error") if isinstance(body, dict) else None


def _insert(row):
    """INSERT IGNORE the row; returns 1 when written, 0 when the sighting already has today's
    row (ux_access_log_sighting: another worker, or an earlier process, wrote it)."""
    conn = get_pooled_db()
    try:
        with conn.cursor() as cur:
            # The pool's connections are autocommit: the row is kept whatever the request did.
            # CURDATE() and the ts default share the session time zone (IST), so the day is ts's.
            cur.execute(
                "INSERT IGNORE INTO access_log (username, role, session_id, client_ip, is_internal, outcome, method,"
                " path, user_agent, detail, sighting_day, sighting_hash) VALUES (%(username)s, %(role)s,"
                " %(session_id)s, %(client_ip)s, %(is_internal)s, %(outcome)s, %(method)s, %(path)s,"
                " %(user_agent)s, %(detail)s, CURDATE(), %(sighting_hash)s)", row)
            return cur.rowcount
    finally:
        return_pooled_db(conn)


def _record(response):
    global _log_backoff_until
    user = g.get("user")
    error_text = _error_text(response) if response.status_code == 403 else None
    outcome, detail = classify_outcome(response.status_code, g.get("access_outcome"), g.get("access_detail"),
                                       error_text)
    ip, internal = client_network()
    who = (user.get("session_id") or user["username"]) if user else None
    if outcome not in OUTCOMES:   # INSERT IGNORE would store '' for a value missing from the ENUM
        logger.error("Access log: unknown outcome %r; row not written", outcome)
        return
    key = (outcome, who, ip, detail)
    if _sightings.seen(key):
        return
    now = time.monotonic()
    if now < _log_backoff_until:
        return
    # Down before the schema first came up: answered from memory, no connect attempt
    if ensure_schema(DB_CONFIG):
        return
    row = {
        "username": truncate(user["username"], _NAME_CHARS) if user else None,
        "role": truncate(logged_role(user), _NAME_CHARS) if user else None,
        "session_id": truncate(user.get("session_id"), _NAME_CHARS) if user else None,
        "client_ip": truncate(ip, _IP_CHARS),
        "is_internal": int(internal),
        "outcome": outcome,
        "method": truncate(request.method, _METHOD_CHARS),
        "path": truncate(request.path, _TEXT_CHARS),
        "user_agent": truncate(request.headers.get("User-Agent"), _TEXT_CHARS),
        "detail": truncate(detail, _TEXT_CHARS),
        "sighting_hash": sighting_hash(*key),
    }
    try:
        written = _insert(row)
    except Exception as exc:   # noqa: BLE001 — any failure: back off, never break the request
        _log_backoff_until = now + DB_BACKOFF_SECONDS
        logger.warning("Access log: could not write (%s); writes paused for %d s", exc, DB_BACKOFF_SECONDS)
        return
    # Remembered either way: a repeat within the window needs no insert attempt
    _sightings.remember(key)
    if written and parse_ip(ip) is None:
        logger.warning("Access log: client address %r is missing or not an address; counted as external", ip)


def make_access_log_hook(dev_bypass=False):
    """Factory for the after_request hook.  Register it before every other after_request hook:
    Flask runs them in reverse, so it runs last and sees the final
    status.  It runs on error-handler and 500 responses too.  A logging failure is logged
    and never breaks the request."""

    def hook(response):
        if _skipped(dev_bypass):
            return response
        try:
            _record(response)
        except Exception:   # noqa: BLE001
            logger.exception("Access log: could not record %s %s", request.method, request.path)
        return response

    return hook

