"""Network gate and access log — the pure part (S013 § 5).

Plain data in, plain data out: no Flask, no database, no clock of its own
(SightingCache takes one).  The shell is access_control.py.
"""

import hashlib
import ipaddress
import re
import threading
import time

from config_rbac import INTERNAL_ONLY_ROLES

# The three private ranges (RFC 1918): every plant address is inside them, and a phone on
# mobile data has a public or carrier-grade NAT (100.64.0.0/10) address, which is not.
# Used by migration v10 and whenever the stored list cannot be read (S013 § 4, § 5.2).
DEFAULT_INTERNAL_NETWORKS = "10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"

OUTCOMES = ("ok", "auth_failed", "denied_network", "denied_perm")

# A business 403's message is kept as the detail up to this length (S013 § 5.4)
DENIED_DETAIL_CHARS = 100

_SEPARATORS = re.compile(r"[,\n\r]+")

# Joins the parts of a sighting key before hashing: a control character no part holds (S013 A1)
_KEY_SEPARATOR = "\x1f"


def parse_networks(text):
    """Comma- or newline-separated CIDR text -> (networks, error).  Entries are trimmed and
    host bits dropped (10.24.0.5/16 -> 10.24.0.0/16).  ``error`` names the first bad entry,
    or says the list is empty; ``networks`` is then empty."""
    entries = [e.strip() for e in _SEPARATORS.split(text or "") if e.strip()]
    networks = []
    for entry in entries:
        try:
            networks.append(ipaddress.ip_network(entry, strict=False))
        except ValueError:
            return [], f"'{entry}' is not a network range such as 10.24.0.0/16"
    if not networks:
        return [], "At least one range is needed"
    return networks, None


def format_networks(networks):
    """The stored form: normalised ranges, comma-separated."""
    return ",".join(str(n) for n in networks)


def parse_ip(ip_text):
    """An address object, or None when the text is not an address.  An IPv4-mapped IPv6
    address (::ffff:10.24.0.5) becomes its IPv4 form, so it matches the IPv4 ranges."""
    try:
        ip = ipaddress.ip_address((ip_text or "").strip())
    except ValueError:
        return None
    if ip.version == 6 and ip.ipv4_mapped is not None:
        return ip.ipv4_mapped
    return ip


def is_internal(ip_text, networks):
    """True when the address is inside one of the ranges, or is loopback (only the server
    itself can present it; keeps dev working whatever the list says).  Unparsable ->
    False: external, fail closed (S013 § 5.1)."""
    ip = parse_ip(ip_text)
    if ip is None:
        return False
    if ip.is_loopback:
        return True
    return any(ip in network for network in networks)


def gate_refuses(roles, internal, internal_only_roles=INTERNAL_ONLY_ROLES):
    """True when an external request must be refused: the user holds a role that may work
    from the plant network only.  Token roles only (S013 § 5.3).  Admin is skipped by the
    caller, and is never in the list anyway."""
    return not internal and any(role in internal_only_roles for role in roles)


def classify_outcome(status, marked_outcome, marked_detail, error_text):
    """(outcome, detail) of a response.  A gate's own mark wins; else a bare 401 is
    auth_failed and a bare 403 is denied_perm with the start of its message (a business
    refusal); anything else on an authenticated request is ok (the user did reach the API,
    a 400 or 500 included)."""
    if marked_outcome:
        return marked_outcome, marked_detail
    if status == 401:
        return "auth_failed", None
    if status == 403:
        return "denied_perm", (error_text or "")[:DENIED_DETAIL_CHARS] or None
    return "ok", None


def truncate(text, length):
    """None stays None; anything else is cut to fit its column."""
    return None if text is None else str(text)[:length]


def sighting_hash(outcome, who, ip, detail):
    """SHA-1 hex of a sighting key (S013 A1): with the IST day, the access_log unique key that
    keeps one row per sighting per day across processes.  SHA-1 for its fixed 40 characters,
    not for secrecy.  A missing part hashes as an empty one."""
    parts = ("" if part is None else str(part) for part in (outcome, who, ip, detail))
    return hashlib.sha1(_KEY_SEPARATOR.join(parts).encode("utf-8")).hexdigest()


class SightingCache:
    """Which sightings this process wrote, or found already written, in the last ``window_seconds``.

    The database keeps one row per sighting per day (S013 A1); this cache only saves the insert
    attempt for repeats within the window.  ``seen(key)`` is asked before writing and
    ``remember(key)`` called only after the insert ran, so a sighting during a database
    outage is written once the database is back.  Entries are kept in the order they were
    remembered; past ``max_entries`` the oldest go.
    """

    def __init__(self, window_seconds, max_entries=10_000, clock=time.monotonic):
        self._window = window_seconds
        self._max = max_entries
        self._clock = clock
        self._seen = {}
        self._lock = threading.Lock()

    def seen(self, key):
        with self._lock:
            at = self._seen.get(key)
            return at is not None and self._clock() - at < self._window

    def remember(self, key):
        with self._lock:
            self._seen.pop(key, None)
            self._seen[key] = self._clock()
            if len(self._seen) > self._max:
                self._prune()

    def clear(self):
        with self._lock:
            self._seen.clear()

    def __len__(self):
        return len(self._seen)

    def _prune(self):
        # Oldest first: expired entries go, then the oldest until under the limit
        now = self._clock()
        for key in list(self._seen):
            if len(self._seen) <= self._max and now - self._seen[key] < self._window:
                break
            del self._seen[key]
