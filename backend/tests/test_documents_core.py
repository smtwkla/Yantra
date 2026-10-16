"""Documents and photos — pure rules (no DB, no Flask)."""

import re
from io import BytesIO

import pytest
from PIL import Image

from documents_core import (
    TYPE_REFUSED, PhotoTooLarge, clean_original_name, detect_file_type, kind_accepts, make_thumbnail,
    safe_download_name, stored_name, thumb_name, validate_document, validate_title,
)
from tests.documents_helpers import image_bytes, jpeg_with_size

PDF_HEAD = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n"
PNG_HEAD = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
WEBP_HEAD = b"RIFF\x24\x00\x00\x00WEBPVP8 "
JPEG_HEAD = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00"
# ISO-BMFF 'ftyp' box with the HEIC brand, as an iPhone writes it
HEIC_HEAD = b"\x00\x00\x00\x18ftypheic\x00\x00\x00\x00"
EXE_HEAD = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00"

EXIF_ORIENTATION = 0x0112
ROTATE_90_CW = 6   # the camera was held upright; the pixels are stored on their side


class TestDetectFileType:

    @pytest.mark.parametrize("head, expected", [
        (PDF_HEAD, ("pdf", "application/pdf")),
        (JPEG_HEAD, ("jpeg", "image/jpeg")),
        (PNG_HEAD, ("png", "image/png")),
        (WEBP_HEAD, ("webp", "image/webp")),
    ])
    def test_real_signatures(self, head, expected):
        assert detect_file_type(head) == expected

    def test_real_images_from_pillow(self):
        img = Image.new("RGB", (2, 2))
        assert detect_file_type(image_bytes(img, "JPEG"))[0] == "jpeg"
        assert detect_file_type(image_bytes(img, "PNG"))[0] == "png"
        assert detect_file_type(image_bytes(img, "WEBP"))[0] == "webp"

    @pytest.mark.parametrize("head", [b"Just some text\n", EXE_HEAD, HEIC_HEAD, b"", None,
                                      b"RIFF\x24\x00\x00\x00WAVEfmt "])
    def test_anything_else_is_none(self, head):
        assert detect_file_type(head) is None


class TestKindAccepts:

    def test_documents_take_pdf_and_photos_take_images(self):
        assert kind_accepts("document", "pdf")
        assert all(kind_accepts("photo", t) for t in ("jpeg", "png", "webp"))

    def test_a_pdf_as_a_photo_and_a_jpeg_as_a_document_are_refused(self):
        assert not kind_accepts("photo", "pdf")
        assert not kind_accepts("document", "jpeg")
        assert not kind_accepts("drawing", "pdf")

    def test_refusal_message(self):
        assert TYPE_REFUSED == "Only PDF documents and JPEG, PNG or WebP photos"


class TestTitle:

    def test_trimmed_and_control_characters_removed(self):
        assert validate_title("  Pump\x00 manual\r\n\x7f ") == ("Pump manual", None)

    @pytest.mark.parametrize("raw", ["", "   ", "\x01\x02", None, 12])
    def test_blank_is_refused(self, raw):
        assert validate_title(raw) == (None, "Title is required")

    def test_length_bounds(self):
        assert validate_title("x" * 200) == ("x" * 200, None)
        assert validate_title("x" * 201) == (None, "Title must be at most 200 characters")

    def test_validate_document(self):
        assert validate_document({"kind": "photo", "title": " Nameplate "}) == (
            {"kind": "photo", "title": "Nameplate"}, [])

    def test_validate_document_errors(self):
        clean, errors = validate_document({"kind": "drawing", "title": ""})
        assert clean == {}
        assert [e["field"] for e in errors] == ["kind", "title"]
        _, errors = validate_document({})
        assert [e["field"] for e in errors] == ["kind", "title"]


class TestNames:

    def test_windows_and_unix_paths_are_cut(self):
        assert clean_original_name(r"C:\Users\me\Desktop\manual.pdf", "t") == "manual.pdf"
        assert clean_original_name("/home/me/photos/IMG_2034.jpg", "t") == "IMG_2034.jpg"

    def test_long_names_are_truncated(self):
        assert clean_original_name("a" * 300 + ".pdf", "t") == "a" * 255

    def test_control_characters_removed(self):
        assert clean_original_name("bad\r\nname.pdf", "t") == "badname.pdf"

    @pytest.mark.parametrize("raw", ["", None, "C:\\folder\\", "\x00"])
    def test_empty_becomes_the_title(self, raw):
        assert clean_original_name(raw, "Pump manual") == "Pump manual"

    def test_stored_name(self):
        name = stored_name("0123456789abcdef0123456789abcdef", "pdf")
        assert re.fullmatch(r"[0-9a-f]{32}\.pdf", name)
        assert thumb_name(name) == f"{name}.thumb.jpg"

    def test_download_name_drops_quotes_slashes_and_control_characters(self):
        assert safe_download_name('He said "go"/no\\yes \'x\'\r\n', "pdf") == "He said gonoyes x.pdf"

    def test_download_name_keeps_non_ascii(self):
        assert safe_download_name("पंप मैनुअल — Ø", "jpg") == "पंप मैनुअल — Ø.jpg"

    def test_download_name_of_nothing_but_unsafe_characters(self):
        assert safe_download_name("///", "pdf") == "file.pdf"


class TestThumbnail:

    def _open(self, data):
        img = Image.open(BytesIO(data))
        img.load()
        return img

    def test_exif_rotated_jpeg_gives_an_upright_thumbnail(self):
        # Stored landscape (40 x 20) with "rotate 90" -> shown portrait (20 x 40)
        img = Image.new("RGB", (40, 20), (200, 30, 30))
        exif = img.getexif()
        exif[EXIF_ORIENTATION] = ROTATE_90_CW
        thumb = self._open(make_thumbnail(image_bytes(img, "JPEG", exif=exif.tobytes())))
        assert thumb.format == "JPEG"
        assert thumb.size == (20, 40)
        assert EXIF_ORIENTATION not in thumb.getexif()

    def test_large_photo_is_shrunk_into_the_box(self):
        thumb = self._open(make_thumbnail(image_bytes(Image.new("RGB", (1600, 1200)), "JPEG")))
        assert thumb.size == (400, 300)

    def test_transparent_png_gets_a_white_background(self):
        thumb = self._open(make_thumbnail(image_bytes(Image.new("RGBA", (10, 10), (0, 0, 0, 0)), "PNG")))
        assert thumb.mode == "RGB"
        assert all(channel >= 250 for channel in thumb.getpixel((0, 0)))

    def test_palette_png_with_transparency_gets_a_white_background(self):
        img = Image.new("P", (10, 10), 0)
        img.putpalette([0, 0, 0] * 256)
        thumb = self._open(make_thumbnail(image_bytes(img, "PNG", transparency=0)))
        assert all(channel >= 250 for channel in thumb.getpixel((0, 0)))

    def test_webp(self):
        thumb = self._open(make_thumbnail(image_bytes(Image.new("RGB", (30, 30)), "WEBP")))
        assert thumb.format == "JPEG"

    def test_header_over_the_cap_is_refused(self):
        with pytest.raises(PhotoTooLarge, match=r"Photo too large \(64 megapixels\)"):
            make_thumbnail(jpeg_with_size(8000, 8000))

    def test_header_just_at_the_cap_is_not_refused_by_it(self):
        # 50 MP exactly passes the cap (libjpeg pads the tiny body; a draft decode keeps it cheap)
        make_thumbnail(jpeg_with_size(10000, 5000))

    def test_pillow_bomb_limit_is_also_a_refusal(self):
        with pytest.raises(PhotoTooLarge, match="over 50 megapixels"):
            make_thumbnail(jpeg_with_size(15000, 15000))

    def test_truncated_jpeg_gives_none(self):
        data = image_bytes(Image.new("RGB", (200, 200), (10, 120, 200)), "JPEG")
        assert make_thumbnail(data[:len(data) // 2]) is None

    @pytest.mark.parametrize("data", [b"\xff\xd8\xff" + b"garbage" * 20, PDF_HEAD, b""])
    def test_unreadable_gives_none(self, data):
        assert make_thumbnail(data) is None
