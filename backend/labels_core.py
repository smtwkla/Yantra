"""QR labels — the pure rules (docs/steps/S014-qr-labels/1-brief.md).

- The link a label carries: the label base address + "/e/" + the node's code.  The code is
  the permanent tag number (ISO 14224 § 8), so a printed label stays true after a move.
- The QR symbol (ISO/IEC 18004): error-correction level Q (25 % of the symbol may be dirty
  or torn and it still reads: a paper label on a machine), a 4-module quiet zone, the
  smallest version that fits.  As SVG, so it prints sharp at 38 mm.
- Which nodes a print run covers: the selection, optionally with its parts.

No database, no Flask: plain data in, plain data out.
"""

import re
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit

import qrcode
from qrcode.image.svg import SvgPathImage

from equipment_core import SCRAPPED

# Equipment codes as issued (S002): a 2-4 letter class prefix and at least three digits;
# 12 characters is the column's width
CODE_RE = re.compile(r"^[A-Z]{2,4}[0-9]{3,8}$")
CODE_MAX_LENGTH = 12

MAX_LABELS_PER_REQUEST = 300
TOO_MANY_LABELS = f"Too many labels — print in smaller groups (at most {MAX_LABELS_PER_REQUEST})"

# Kept short so the longest link (40 + "/e/" + 12 = 55 bytes) stays at version 5 at level Q
BASE_URL_MAX_LENGTH = 40
_SCHEMES = ("https", "http")
# Host names and IPv4 addresses: letters, digits, dots and hyphens; nothing that would need
# escaping in a link or that could smuggle text into it
_HOST_RE = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)*$")

QR_BORDER_MODULES = 4   # the quiet zone ISO/IEC 18004 asks for


def parse_code(text):
    """The equipment code in a label link → upper-case code, or None when it cannot be a
    code (so the caller answers 404 without a query).  Codes are stored upper-case (S002)."""
    if not isinstance(text, str) or len(text) > CODE_MAX_LENGTH:
        return None
    code = text.upper()
    return code if CODE_RE.fullmatch(code) else None


def label_url(base_url, code):
    """The link on the label.  ``base_url`` is normalised (no trailing slash); the strip
    only guards against a double slash if a caller ever passes one."""
    return f"{base_url.rstrip('/')}/e/{code}"


def normalise_base_url(text):
    """The label link address as typed → ``(url, None)`` or ``(None, message)``.

    Scheme https or http; a host (a port is allowed), no user name or password; no path,
    query or fragment (a lone trailing slash is dropped); the host lower-cased; at most
    BASE_URL_MAX_LENGTH characters."""
    PORT_MESSAGE = "The port must be a number from 1 to 65535"
    message = "Enter an address like https://vel-yantra.mspv.app — no path after the host"
    if not isinstance(text, str):
        return None, message
    text = text.strip()
    if "?" in text or "#" in text:
        return None, message
    parts = urlsplit(text)
    if parts.scheme not in _SCHEMES:
        return None, "The address must start with https:// or http://"
    if "@" in parts.netloc:
        return None, "The address must not hold a user name or password"
    if parts.path not in ("", "/"):
        return None, message
    host = (parts.hostname or "").lower()
    if not _HOST_RE.fullmatch(host):
        return None, message
    try:
        port = parts.port
    except ValueError:
        return None, PORT_MESSAGE
    if port == 0:
        return None, PORT_MESSAGE
    url = f"{parts.scheme}://{host}" + (f":{port}" if port is not None else "")
    if len(url) > BASE_URL_MAX_LENGTH:
        return None, f"At most {BASE_URL_MAX_LENGTH} characters, so the QR code stays coarse enough to scan"
    return url, None


def make_qr(text):
    """The QR symbol for ``text``, built: level Q, 4-module quiet zone, the smallest version."""
    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_Q,
                       border=QR_BORDER_MODULES, image_factory=SvgPathImage)
    qr.add_data(text)
    qr.make(fit=True)
    return qr


def qr_svg(text):
    """One ``<svg>`` element with a viewBox and a single path: no XML declaration and no
    fixed width or height, so CSS sizes it to the label's box.  The library's path id is
    dropped too: a sheet holds many of these and an id must be unique in a page."""
    svg = make_qr(text).make_image().get_image()
    for attribute in ("width", "height"):
        svg.attrib.pop(attribute, None)
    for path in svg.iter():
        path.attrib.pop("id", None)
    return ET.tostring(svg, encoding="unicode")


def expand_selection(selected_ids, rows, with_parts):
    """The nodes to print, in order → ``(rows, None)`` or ``(None, message)``.

    ``rows`` are the fetched nodes (dicts with id, parent_id, code, lifecycle): the selected
    ones and, with parts, their children and grandchildren.  Each selected node comes in
    the order selected, then its parts level by level, by code.  Scrapped parts are left
    out (a scrapped part is gone; a scrapped node that was selected is printed).  A node
    already listed is not listed again, so a parent and its own part both ticked give one
    label each.  More than MAX_LABELS_PER_REQUEST → the message."""
    by_id = {row["id"]: row for row in rows}
    children = {}
    for row in rows:  # live_parts() sorts by code
        if row["parent_id"] is not None:
            children.setdefault(row["parent_id"], []).append(row)

    def live_parts(parent_ids):
        found = [c for pid in parent_ids for c in children.get(pid, []) if c["lifecycle"] != SCRAPPED]
        return sorted(found, key=lambda r: r["code"])

    ordered, seen = [], set()
    for node_id in selected_ids:
        group = [by_id[node_id]]
        if with_parts:
            level_one = live_parts([node_id])
            group += level_one + live_parts([c["id"] for c in level_one])
        for row in group:
            if row["id"] not in seen:
                seen.add(row["id"])
                ordered.append(row)
    if len(ordered) > MAX_LABELS_PER_REQUEST:
        return None, TOO_MANY_LABELS
    return ordered, None
