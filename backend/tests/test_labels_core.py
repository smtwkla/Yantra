"""QR labels — pure rules (no DB, no Flask; S014)."""

import pytest
import qrcode

from labels_core import (
    BASE_URL_MAX_LENGTH, MAX_LABELS_PER_REQUEST, TOO_MANY_LABELS, expand_selection, label_url, make_qr,
    normalise_base_url, parse_code, qr_svg,
)

# The production address (settings.DEFAULT_LABEL_BASE_URL); written out so this test stays pure
DEFAULT_ADDRESS = "https://vel-yantra.mspv.app"


class TestParseCode:

    @pytest.mark.parametrize("text, code", [("VBM001", "VBM001"), ("vbm001", "VBM001"), ("AB123", "AB123"),
                                            ("ABCD12345678", "ABCD12345678")])
    def test_a_code(self, text, code):
        assert parse_code(text) == code

    @pytest.mark.parametrize("text", ["", "V001", "VBM01", "ABCDE001", "VBM-001", "ABCD123456789", "001VBM",
                                      "VBM001X", None, 42])
    def test_not_a_code(self, text):
        assert parse_code(text) is None


class TestLabelUrl:

    def test_the_link(self):
        assert label_url("https://vel-yantra.mspv.app", "VBM001") == "https://vel-yantra.mspv.app/e/VBM001"

    def test_no_double_slash(self):
        assert label_url("https://vel-yantra.mspv.app/", "VBM001") == "https://vel-yantra.mspv.app/e/VBM001"


class TestNormaliseBaseUrl:

    @pytest.mark.parametrize("text, url", [
        ("https://vel-yantra.mspv.app", "https://vel-yantra.mspv.app"),
        ("  https://vel-yantra.mspv.app/  ", "https://vel-yantra.mspv.app"),
        ("HTTPS://Vel-Yantra.MSPV.app", "https://vel-yantra.mspv.app"),
        ("http://10.24.1.5:5176", "http://10.24.1.5:5176"),
    ])
    def test_accepted(self, text, url):
        assert normalise_base_url(text) == (url, None)

    @pytest.mark.parametrize("text", [
        "https://vel-yantra.mspv.app/yantra", "https://vel-yantra.mspv.app/?x=1", "https://vel-yantra.mspv.app?",
        "https://vel-yantra.mspv.app#top", "https://user:pw@vel-yantra.mspv.app", "https://user@vel-yantra.mspv.app",
        "ftp://vel-yantra.mspv.app", "javascript:alert(1)", "vel-yantra.mspv.app", "https://", "https://a b.app",
        "https://vel<yantra>.app", "https://host:port", "https://host:99999", "https://x.in:0", "", None, 5,
    ])
    def test_refused(self, text):
        url, message = normalise_base_url(text)
        assert url is None and message

    def test_at_most_40_characters(self):
        host = "a" * (BASE_URL_MAX_LENGTH - len("https://.in")) + ".in"
        assert normalise_base_url(f"https://{host}") == (f"https://{host}", None)
        url, message = normalise_base_url(f"https://a{host}")
        assert url is None and "40" in message


class TestQrSvg:

    def test_level_q_and_quiet_zone(self):
        qr = make_qr("https://vel-yantra.mspv.app/e/VBM001")
        assert qr.error_correction == qrcode.constants.ERROR_CORRECT_Q
        assert qr.border == 4

    def test_one_scalable_svg_element(self):
        svg = qr_svg("https://vel-yantra.mspv.app/e/VBM001")
        assert svg.startswith("<svg") and svg.endswith("</svg>")
        assert "<?xml" not in svg
        assert "viewBox=" in svg
        assert " width=" not in svg.split(">", 1)[0] and " height=" not in svg.split(">", 1)[0]
        assert svg.count("<path") == 1
        assert " id=" not in svg

    def test_the_longest_code_at_the_default_address_is_version_4(self):
        assert make_qr(label_url(DEFAULT_ADDRESS, "ABCD12345678")).version <= 4

    def test_the_longest_code_at_a_40_character_address_is_version_5(self):
        base = "https://" + "a" * (BASE_URL_MAX_LENGTH - len("https://.in")) + ".in"
        assert len(base) == BASE_URL_MAX_LENGTH
        assert make_qr(label_url(base, "ABCD12345678")).version <= 5


def _row(node_id, code, parent_id=None, status="in_service"):
    return {"id": node_id, "code": code, "parent_id": parent_id, "status": status}


# 1 PRS001 ─┬─ 3 MOT002 ── 5 BRG001
#           └─ 2 GBX001 ── 6 BRG002 (scrapped)
#                       └─ 7 SEL001
# 4 PRS002
TREE = [_row(1, "PRS001"), _row(4, "PRS002"), _row(3, "MOT002", 1), _row(2, "GBX001", 1), _row(5, "BRG001", 3),
        _row(6, "BRG002", 2, "scrapped"), _row(7, "SEL001", 2)]


def _ids(result):
    rows, message = result
    assert message is None
    return [r["id"] for r in rows]


class TestExpandSelection:

    def test_without_parts_in_the_order_selected(self):
        assert _ids(expand_selection([4, 1], TREE, False)) == [4, 1]

    def test_with_parts_level_by_level_by_code(self):
        assert _ids(expand_selection([1], TREE, True)) == [1, 2, 3, 5, 7]

    def test_a_scrapped_part_is_left_out(self):
        assert 6 not in _ids(expand_selection([2], TREE, True))

    def test_a_selected_scrapped_node_is_printed(self):
        assert _ids(expand_selection([6], TREE, True)) == [6]

    def test_a_parent_and_its_own_part_selected_give_one_label_each(self):
        assert _ids(expand_selection([1, 3], TREE, True)) == [1, 2, 3, 5, 7]
        assert _ids(expand_selection([3, 1], TREE, True)) == [3, 5, 1, 2, 7]

    def test_the_cap_after_expansion(self):
        parent = _row(1, "PRS001")
        parts = [_row(i, f"MOT{i:03d}", 1) for i in range(2, MAX_LABELS_PER_REQUEST + 2)]
        assert expand_selection([1], [parent, *parts], True) == (None, TOO_MANY_LABELS)
        rows, message = expand_selection([1], [parent, *parts[:-1]], True)
        assert message is None and len(rows) == MAX_LABELS_PER_REQUEST

    def test_nothing_selected(self):
        assert expand_selection([], [], True) == ([], None)
