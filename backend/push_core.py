"""Web push — pure rules for the push channel only (docs/steps/S021-alerts-push/1-brief.md § 3,
§ 5.1, § 5.4; no DB, no clock, no Flask).  The alerts themselves (who, when, the text) are
alerts_core's, the same for every channel.

- the address check: a browser gives the push address and the worker posts to it, so only
  HTTPS addresses at the known push services are accepted (ISO 27001 A 8.20, OWASP SSRF);
- the endpoint hash (the unique key of a device: endpoints are too long for an index);
- the device label from a User-Agent string;
- how the push service's answer maps to what the send task does next;
- the push message's payload, as the service worker (frontend/public/sw.js) reads it.
"""

import hashlib
import re
from urllib.parse import urlsplit

# The parser requests (inside pywebpush) uses to find the host it connects to; urllib3 comes
# with requests.  The address check asks it too, so the host checked is the host posted to (CR1-01).
from urllib3.exceptions import LocationParseError
from urllib3.util import parse_url

# The push services Yantra posts to; a host matches itself or any sub-domain.  Samsung
# Internet may use one of its own: its host is added only once a real subscription shows it
# (§ 5.4, BR3-05 — the refusal is logged with the host).
ALLOWED_PUSH_HOSTS = (
    "fcm.googleapis.com",          # Chrome and Edge on Android; Chrome on a computer
    "push.apple.com",              # Safari on iPhone (Home Screen app) and Mac: web.push.apple.com
    "push.services.mozilla.com",   # Firefox
    "notify.windows.com",          # Edge on Windows (WNS)
)

ENDPOINT_MAX = 1000                # push_subscriptions.endpoint
P256DH_MAX = 200
AUTH_MAX = 100
LABEL_MAX = 100
UNKNOWN_DEVICE = "Unknown device"

# How long the push service keeps an undelivered message: a breakdown alert that reaches a
# phone switched on the next morning helps nobody (§ 5.1)
ALERT_TTL_SECONDS = 3600
TEST_TTL_SECONDS = 300

BROWSER_CANNOT = ("This browser cannot get notifications. Use Chrome on Android, or open Yantra from the "
                  "Home Screen on an iPhone.")
SUBSCRIPTION_UNUSABLE = "This browser sent a subscription Yantra cannot use. Turn notifications off and on again."

_HASH_RE = re.compile(r"[0-9a-f]{64}")
_BASE64URL_RE = re.compile(r"[A-Za-z0-9_-]+={0,2}")
_DIGITS_RE = re.compile(r"[0-9]+")
# Printable ASCII without space, and no backslash: urlsplit and urllib3 read a backslash, a
# space or a control character differently, so an address holding one is refused (CR1-01)
_ADDRESS_RE = re.compile(r"[\x21-\x5b\x5d-\x7e]+")
# The authority as a bare DNS name: labels of a-z, 0-9 and "-", no trailing dot.  This rules
# out user-info ("@"), any port (":"), IPv6 literals ("[") and percent-encoding ("%")
_HOST_RE = re.compile(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+")

# What the push_send task does with the push service's answer (§ 5.1)
SENT = "sent"                # done; last_sent_at set
GONE = "gone"                # the device unsubscribed or its data was cleared: delete the row; done
REFUSED = "refused"          # our fault (payload, keys): NoRetry
RETRY_LATER = "retry_later"  # 429 with a usable Retry-After: RetryLater(after_seconds)
RETRY = "retry"              # anything else: the queue's own back-off

_SENT_STATUSES = (200, 201, 202)
_GONE_STATUSES = (404, 410)
_REFUSED_STATUSES = (400, 403, 413)
_TOO_MANY = 429


def refused_host(endpoint):
    """None when ``endpoint`` is an address Yantra may post to: ``https://``, printable ASCII
    with no backslash, an authority that is a bare DNS name (no user-info, no port, no IP
    literal, no percent-encoding), the same host for urlsplit and for urllib3 (the parser
    requests posts with), and a host that is one of ALLOWED_PUSH_HOSTS or a sub-domain of one.
    Otherwise the host to log ("" when there is none) — never the full address, which
    identifies a device."""
    if not isinstance(endpoint, str) or not endpoint or len(endpoint) > ENDPOINT_MAX or endpoint != endpoint.strip():
        return ""
    try:
        parts = urlsplit(endpoint)
    except ValueError:
        return ""
    host = (parts.hostname or "").lower()
    if (parts.scheme != "https" or not host or _ADDRESS_RE.fullmatch(endpoint) is None
            or _HOST_RE.fullmatch(parts.netloc.lower()) is None):
        return host
    try:
        posted = parse_url(endpoint)
    except LocationParseError:
        return host
    if posted.scheme != "https" or posted.auth is not None or posted.port is not None or posted.host != host:
        return host
    if any(host == allowed or host.endswith(f".{allowed}") for allowed in ALLOWED_PUSH_HOSTS):
        return None
    return host


def endpoint_hash(endpoint):
    """The device's key: the lowercase hex SHA-256 of the endpoint, as the page's
    crypto.subtle.digest makes it (BR2-12)."""
    return hashlib.sha256(endpoint.encode("utf-8")).hexdigest()


def is_endpoint_hash(text):
    return isinstance(text, str) and _HASH_RE.fullmatch(text) is not None


def _key(value, maximum):
    return isinstance(value, str) and 0 < len(value) <= maximum and _BASE64URL_RE.fullmatch(value) is not None


def validate_subscription(body, _creating=True):
    """``{endpoint, keys: {p256dh, auth}}`` as the browser's PushSubscription.toJSON() gives it
    -> ``(clean, errors)``.  The shape only; the address check is refused_host's, so the shell
    can log the refused host."""
    endpoint = body.get("endpoint")
    keys = body.get("keys")
    if not isinstance(endpoint, str) or not isinstance(keys, dict):
        return {}, [{"field": None, "message": SUBSCRIPTION_UNUSABLE}]
    if not _key(keys.get("p256dh"), P256DH_MAX) or not _key(keys.get("auth"), AUTH_MAX):
        return {}, [{"field": None, "message": SUBSCRIPTION_UNUSABLE}]
    return {"endpoint": endpoint, "p256dh": keys["p256dh"], "auth": keys["auth"]}, []


# (User-Agent marker, name), first match wins: Samsung Internet, Edge and Opera also say
# "Chrome", and Chrome also says "Safari"
_SYSTEMS = (("Android", "Android"), ("iPhone", "iPhone"), ("iPad", "iPad"), ("CrOS", "ChromeOS"),
            ("Windows", "Windows"), ("Macintosh", "Mac"), ("Linux", "Linux"))
_BROWSERS = (("SamsungBrowser/", "Samsung Internet"), ("EdgA/", "Edge"), ("EdgiOS/", "Edge"), ("Edg/", "Edge"),
             ("OPR/", "Opera"), ("FxiOS/", "Firefox"), ("Firefox/", "Firefox"), ("CriOS/", "Chrome"),
             ("Chrome/", "Chrome"), ("Safari/", "Safari"))


def device_label(user_agent):
    """"Android · Chrome", "iPhone · Safari", … from a User-Agent string; UNKNOWN_DEVICE when it
    names neither.  An iPhone's Home Screen app says no browser, so it reads "iPhone"."""
    text = user_agent if isinstance(user_agent, str) else ""
    parts = [next((name for marker, name in table if marker in text), None) for table in (_SYSTEMS, _BROWSERS)]
    label = " · ".join(part for part in parts if part)
    return label[:LABEL_MAX] or UNKNOWN_DEVICE


def parse_retry_after(value):
    """Retry-After as a whole number of seconds -> int; an HTTP date, or anything else, counts
    as absent -> None (BR2-03)."""
    if isinstance(value, str) and _DIGITS_RE.fullmatch(value.strip()):
        return int(value.strip())
    return None


def send_outcome(status, retry_after):
    """The push service's answer -> ``(outcome, after_seconds)``; ``after_seconds`` is set for
    RETRY_LATER only.  200 counts as sent with 201 and 202: the message was taken."""
    if status in _SENT_STATUSES:
        return SENT, None
    if status in _GONE_STATUSES:
        return GONE, None
    if status in _REFUSED_STATUSES:
        return REFUSED, None
    if status == _TOO_MANY:
        seconds = parse_retry_after(retry_after)
        if seconds is not None:
            return RETRY_LATER, seconds
    return RETRY, None


def send_task_payload(subscription_id, message, ttl):
    """The push_send task's payload (§ 5.1) from an alert's message (alerts_core.message): quiet
    alerts go with Urgency low and no sound."""
    return {
        "subscription_id": subscription_id,
        "title": message["title"],
        "body": message["body"],
        "path": message["path"],
        "tag": message["tag"],
        "urgency": "low" if message["quiet"] else "high",
        "silent": message["quiet"],
        "ttl": ttl,
    }


def push_data(task_payload):
    """What the service worker receives (encrypted end to end, RFC 8291): the text, the path
    the tap opens, the tag that replaces an earlier alert of the same ticket, and silent."""
    return {key: task_payload[key] for key in ("title", "body", "path", "tag", "silent")}
