"""Pure validation of the masters' input — no DB, no Flask."""

import pytest

from masters_core import (
    normalise_username, validate_equipment_class, validate_equipment_type, validate_site, validate_unit,
    validate_unit_ids, validate_username,
)


def _fields(errors):
    return [e["field"] for e in errors]


class TestEquipmentClassCode:

    @pytest.mark.parametrize("code, ok", [
        ("V", False), ("VB", True), ("VBM", True), ("VBMX", True), ("VBMXY", False),
        ("V1M", False), ("V-M", False), ("", False),
    ])
    def test_boundaries(self, code, ok):
        clean, errors = validate_equipment_class({"code": code, "name": "Vibrating mill"}, creating=True)
        assert (errors == []) is ok
        if not ok:
            assert _fields(errors) == ["code"]

    def test_code_is_stripped_and_upper_cased(self):
        clean, errors = validate_equipment_class({"code": " vbm ", "name": "x"}, creating=True)
        assert errors == []
        assert clean["code"] == "VBM"


class TestEquipmentType:

    def test_create_happy_path(self):
        clean, errors = validate_equipment_type({"class_id": 3, "name": "  Closed execution "}, creating=True)
        assert errors == []
        assert clean == {"class_id": 3, "name": "Closed execution"}

    def test_create_needs_class_and_name(self):
        _, errors = validate_equipment_type({}, creating=True)
        assert sorted(_fields(errors)) == ["class_id", "name"]

    @pytest.mark.parametrize("name", ["", "   ", None, 5, "x" * 101])
    def test_bad_name(self, name):
        _, errors = validate_equipment_type({"class_id": 3, "name": name}, creating=True)
        assert _fields(errors) == ["name"]

    def test_name_of_100_characters_is_fine(self):
        assert validate_equipment_type({"class_id": 3, "name": "x" * 100}, creating=True)[1] == []

    @pytest.mark.parametrize("name", ["none", "None", "NONE", " none "])
    def test_none_is_reserved(self, name):
        _, errors = validate_equipment_type({"class_id": 3, "name": name}, creating=True)
        assert _fields(errors) == ["name"]

    def test_a_name_containing_none_is_fine(self):
        assert validate_equipment_type({"class_id": 3, "name": "None-return valve"}, creating=True)[1] == []

    @pytest.mark.parametrize("class_id", [0, -1, "3", True, None, 1.5])
    def test_bad_class_id(self, class_id):
        _, errors = validate_equipment_type({"class_id": class_id, "name": "x"}, creating=True)
        assert _fields(errors) == ["class_id"]

    def test_update_leaves_absent_fields_out(self):
        assert validate_equipment_type({"name": "Open execution"}, creating=False) == ({"name": "Open execution"}, [])

    def test_update_parses_class_id_as_an_id(self):
        # Whether it changed is the shell's decision; the validator only parses it
        assert validate_equipment_type({"class_id": 4}, creating=False) == ({"class_id": 4}, [])
        assert _fields(validate_equipment_type({"class_id": "4"}, creating=False)[1]) == ["class_id"]

    @pytest.mark.parametrize("raw, expected", [(True, 1), (False, 0), (1, 1), (0, 0)])
    def test_active_reaches_the_update(self, raw, expected):
        assert validate_equipment_type({"active": raw}, creating=False) == ({"active": expected}, [])


class TestSiteCode:

    @pytest.mark.parametrize("code, ok", [
        ("S", False), ("SM", True), ("SMTW-KP", True), ("AGRI-VKM", True),
        ("SMTW.KP", False), ("1SMTW", False), ("-SM", False), ("A" * 20, True), ("A" * 21, False),
    ])
    def test_boundaries(self, code, ok):
        _, errors = validate_site({"code": code, "name": "Site"}, creating=True)
        assert (errors == []) is ok


class TestUnitCode:

    @pytest.mark.parametrize("code, ok", [
        ("M", False), ("M1", True), ("MCC1", True), ("1A", True), ("FW-MILL", True),
        ("FW.MILL", False), ("-A", False),
    ])
    def test_boundaries(self, code, ok):
        _, errors = validate_unit({"site_id": 1, "code": code, "name": "Unit"}, creating=True)
        assert (errors == []) is ok


class TestRequiredFields:

    def test_create_needs_code_and_name(self):
        _, errors = validate_site({}, creating=True)
        assert sorted(_fields(errors)) == ["code", "name"]

    def test_unit_create_needs_site(self):
        _, errors = validate_unit({"code": "MCC1", "name": "MCC 1"}, creating=True)
        assert _fields(errors) == ["site_id"]

    def test_update_leaves_absent_fields_out(self):
        clean, errors = validate_site({"name": "New name"}, creating=False)
        assert errors == []
        assert clean == {"name": "New name"}

    @pytest.mark.parametrize("name", ["", "   ", None, 5])
    def test_blank_or_non_text_name_is_rejected(self, name):
        _, errors = validate_site({"code": "SM", "name": name}, creating=True)
        assert _fields(errors) == ["name"]

    def test_name_too_long(self):
        _, errors = validate_site({"code": "SM", "name": "x" * 101}, creating=True)
        assert _fields(errors) == ["name"]

    def test_errors_have_field_and_message(self):
        _, errors = validate_site({"code": "!", "name": "x"}, creating=True)
        assert set(errors[0]) == {"field", "message"}
        assert errors[0]["message"]

    @pytest.mark.parametrize("site_id", [0, -1, "1", True, None, 1.5])
    def test_bad_site_id(self, site_id):
        _, errors = validate_unit({"site_id": site_id, "code": "MCC1", "name": "x"}, creating=True)
        assert _fields(errors) == ["site_id"]


class TestOneerpWarehouse:

    def test_stripped_but_not_upper_cased(self):
        clean, _ = validate_unit({"site_id": 1, "code": "MCC1", "name": "x",
                                  "oneerp_warehouse": "  SMTW.MCC1 - Smtw  "}, creating=True)
        assert clean["oneerp_warehouse"] == "SMTW.MCC1 - Smtw"

    @pytest.mark.parametrize("raw", ["", "   ", None])
    def test_empty_becomes_none(self, raw):
        clean, errors = validate_unit({"site_id": 1, "code": "MCC1", "name": "x",
                                       "oneerp_warehouse": raw}, creating=True)
        assert errors == []
        assert clean["oneerp_warehouse"] is None

    def test_too_long(self):
        _, errors = validate_unit({"site_id": 1, "code": "MCC1", "name": "x",
                                   "oneerp_warehouse": "w" * 141}, creating=True)
        assert _fields(errors) == ["oneerp_warehouse"]


class TestAddressAndActive:

    def test_empty_address_becomes_none(self):
        clean, _ = validate_site({"code": "SM", "name": "x", "address": "  "}, creating=True)
        assert clean["address"] is None

    @pytest.mark.parametrize("raw, expected", [(True, 1), (False, 0), (1, 1), (0, 0)])
    def test_active_accepts_flags(self, raw, expected):
        clean, errors = validate_site({"active": raw}, creating=False)
        assert errors == []
        assert clean["active"] == expected

    @pytest.mark.parametrize("raw", ["yes", 2, None])
    def test_active_rejects_other_values(self, raw):
        _, errors = validate_site({"active": raw}, creating=False)
        assert _fields(errors) == ["active"]


class TestIsDefault:

    @pytest.mark.parametrize("raw, expected", [(True, 1), (False, 0), (1, 1), (0, 0)])
    def test_accepts_flags(self, raw, expected):
        clean, errors = validate_site({"is_default": raw}, creating=False)
        assert errors == []
        assert clean["is_default"] == expected

    @pytest.mark.parametrize("raw", ["yes", 2, None, "1"])
    def test_rejects_other_values(self, raw):
        _, errors = validate_site({"is_default": raw}, creating=False)
        assert _fields(errors) == ["is_default"]

    def test_optional_on_create(self):
        clean, errors = validate_site({"code": "SM", "name": "x"}, creating=True)
        assert errors == []
        assert "is_default" not in clean


class TestUsername:

    def test_normalised_to_lower_case_stripped(self):
        assert normalise_username("  JDoe ") == "jdoe"

    @pytest.mark.parametrize("name, ok", [
        ("jdoe", True), ("j.doe", True), ("j.doe@smtw.in", True), ("a", True),
        ("", False), (".doe", False), ("j doe", False), ("j/doe", False), ("a" * 101, False),
    ])
    def test_format(self, name, ok):
        username, errors = validate_username(name)
        assert (errors == []) is ok

    def test_returns_normalised_name(self):
        assert validate_username(" JDoe ")[0] == "jdoe"


class TestUnitIds:

    def test_valid_list_is_deduplicated_in_order(self):
        assert validate_unit_ids([3, 1, 3, 2]) == ([3, 1, 2], [])

    def test_empty_list_is_valid(self):
        assert validate_unit_ids([]) == ([], [])

    @pytest.mark.parametrize("raw", [None, "1", [1, "2"], [True], [0], [-1], [1.5]])
    def test_invalid(self, raw):
        _, errors = validate_unit_ids(raw)
        assert _fields(errors) == ["unit_ids"]
