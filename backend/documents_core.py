"""Documents and photos on equipment — pure rules (no DB, no Flask, no clock).

docs/steps/S006-equipment-documents/1-brief.md.  Bytes in, bytes out: the shell
(documents.py) reads the upload, passes the bytes here, and stores what comes back.

Pillow is a library, not a framework, so the thumbnail is made here too.
"""

import re
from io import BytesIO

from PIL import Image, ImageOps

KINDS = ("document", "photo")

TITLE_MAX = 200
ORIGINAL_NAME_MAX = 255

# Detected file type -> (content type, stored extension)
FILE_TYPES = {
    "pdf": ("application/pdf", "pdf"),
    "jpeg": ("image/jpeg", "jpg"),
    "png": ("image/png", "png"),
    "webp": ("image/webp", "webp"),
}

_KIND_TYPES = {
    "document": ("pdf",),
    "photo": ("jpeg", "png", "webp"),
}

TYPE_REFUSED = "Only PDF documents and JPEG, PNG or WebP photos"

# How many first bytes detect_file_type needs (WebP: RIFF, 4 size bytes, WEBP)
SIGNATURE_BYTES = 12

THUMB_BOX = (400, 400)
THUMB_QUALITY = 85
THUMB_SUFFIX = ".thumb.jpg"
THUMB_EXTENSION = "jpg"

# Phones take 12 MP by default and 48 MP at most; above this, decoding could exhaust memory
MAX_MEGAPIXELS = 50
_MAX_PIXELS = MAX_MEGAPIXELS * 1_000_000

_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")
# Path separators and quotes would confuse a Content-Disposition header or a saved file name
_DOWNLOAD_UNSAFE = re.compile(r"[\x00-\x1f\x7f/\\\"']")
# Used when a title is nothing but characters a file name cannot carry
_FALLBACK_DOWNLOAD_STEM = "file"


class PhotoTooLarge(Exception):
    """A photo whose pixel count is above the cap; the route turns it into a 400."""


def detect_file_type(first_bytes):
    """The file's type from its first bytes -> ``(file_type, content_type)``, or None.

    The client's file name and content type are never consulted (ISO 27001 A.8.28)."""
    data = bytes(first_bytes or b"")
    if data.startswith(b"%PDF-"):
        file_type = "pdf"
    elif data.startswith(b"\xff\xd8\xff"):
        file_type = "jpeg"
    elif data.startswith(b"\x89PNG\r\n\x1a\n"):
        file_type = "png"
    elif len(data) >= SIGNATURE_BYTES and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        file_type = "webp"
    else:
        return None
    return file_type, FILE_TYPES[file_type][0]


def kind_accepts(kind, file_type):
    """Documents take PDF; photos take JPEG, PNG and WebP."""
    return file_type in _KIND_TYPES.get(kind, ())


def _strip_control(text):
    return _CONTROL_CHARS.sub("", text)


def validate_title(raw):
    """-> ``(title, None)`` or ``(None, message)``.  Control characters removed, trimmed,
    1-200 characters."""
    title = _strip_control(raw).strip() if isinstance(raw, str) else ""
    if not title:
        return None, "Title is required"
    if len(title) > TITLE_MAX:
        return None, f"Title must be at most {TITLE_MAX} characters"
    return title, None


def validate_document(form):
    """The upload's form fields (``kind``, ``title``) -> ``(clean, errors)``, errors as
    ``[{field, message}]`` like the other validators."""
    clean, errors = {}, []
    kind = form.get("kind")
    if kind in KINDS:
        clean["kind"] = kind
    else:
        errors.append({"field": "kind", "message": "Kind must be document or photo"})
    title, message = validate_title(form.get("title"))
    if message:
        errors.append({"field": "title", "message": message})
    else:
        clean["title"] = title
    return clean, errors


def clean_original_name(raw, title):
    """The client's file name for display: the part after the last / or \\, control
    characters removed, at most 255 characters; empty -> the title."""
    name = raw if isinstance(raw, str) else ""
    name = re.split(r"[/\\]", name)[-1]
    name = _strip_control(name).strip()[:ORIGINAL_NAME_MAX]
    return name or title[:ORIGINAL_NAME_MAX]


def stored_name(token, ext):
    """The system-generated file name: a random token and the detected type's extension."""
    return f"{token}.{ext}"


def thumb_name(stored):
    return f"{stored}{THUMB_SUFFIX}"


def safe_download_name(title, ext):
    """``<title>.<ext>`` with path separators, quotes and control characters dropped.
    Non-ASCII stays: send_file writes it as RFC 5987 ``filename*``."""
    stem = _DOWNLOAD_UNSAFE.sub("", title).strip() or _FALLBACK_DOWNLOAD_STEM
    return f"{stem}.{ext}"


def _megapixels(pixels):
    return f"{round(pixels / 1_000_000, 1):g}"


def _has_transparency(img):
    return img.mode in ("RGBA", "LA", "PA") or "transparency" in img.info


def _flatten_on_white(img):
    """An image with transparency onto a white canvas, using its alpha as the mask; a plain
    convert("RGB") would drop the alpha and turn transparent areas black."""
    rgba = img.convert("RGBA")
    canvas = Image.new("RGB", rgba.size, (255, 255, 255))
    canvas.paste(rgba, mask=rgba.getchannel("A"))
    return canvas


def make_thumbnail(data):
    """A JPEG thumbnail (at most 400 x 400, upright, no EXIF) of a photo -> bytes, or None
    when Pillow cannot read the image.  Raises PhotoTooLarge above the pixel cap.

    The size is read from the header before anything is decoded; ``thumbnail`` runs before
    ``exif_transpose`` so a JPEG decodes at a reduced scale (brief § 5.3)."""
    try:
        img = Image.open(BytesIO(data), formats=["JPEG", "PNG", "WEBP"])
    except Image.DecompressionBombError as exc:
        # Pillow's own limit (about 179 MP) — a backstop behind the cap below
        raise PhotoTooLarge(f"Photo too large (over {MAX_MEGAPIXELS} megapixels)") from exc
    except (OSError, ValueError, SyntaxError):
        return None
    with img:
        width, height = img.size
        if width * height > _MAX_PIXELS:
            raise PhotoTooLarge(f"Photo too large ({_megapixels(width * height)} megapixels)")
        try:
            img.thumbnail(THUMB_BOX)
            upright = ImageOps.exif_transpose(img)
            flat = _flatten_on_white(upright) if _has_transparency(upright) else upright.convert("RGB")
            out = BytesIO()
            flat.save(out, format="JPEG", quality=THUMB_QUALITY)
        except (OSError, ValueError, SyntaxError):
            return None
    return out.getvalue()
