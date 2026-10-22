"""A fresh VAPID key pair (RFC 8292) in the wire forms config.VAPID_* hold (S021 § 3, BR1-06,
BR2-12).  Shared by tooling/dev/make_vapid_keys.py (dev, and once for production), the pytest
fixture and the e2e backend.  It imports neither config nor Flask, so the dev tool runs without
secrets_app.py.
"""

import base64

from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from py_vapid import Vapid

PRIVATE_KEY_BYTES = 32


def _b64url(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def make_key_pair():
    """-> ``(public_key, private_key)``: the raw 65-byte uncompressed P-256 point (87
    characters, what the browser's applicationServerKey takes) and the raw 32-byte scalar (43
    characters, what py_vapid.Vapid.from_string reads), each base64url without padding."""
    vapid = Vapid()
    vapid.generate_keys()
    public = vapid.public_key.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
    private = vapid.private_key.private_numbers().private_value.to_bytes(PRIVATE_KEY_BYTES, "big")
    return _b64url(public), _b64url(private)
