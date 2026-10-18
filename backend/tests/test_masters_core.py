"""Pure validation of the masters' input — no DB, no Flask."""

import pytest

from masters_core import (
    NO_LOGIN_ROLE_MESSAGE, model_label, no_login_role_error, normalise_username, technician_only,
    validate_equipment_class, validate_equipment_model, validate_equipment_type, validate_manufacturer,
    validate_person, validate_site, validate_site_row, validate_site_rows, validate_trade, validate_unit,
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


class TestManufacturer:
    """S012 § 5.1: one spelling per maker (ISO 8000)."""

    def test_name_is_trimmed_and_inner_spaces_collapsed(self):
        clean, errors = validate_manufacturer({"name": "  Atlas   Copco \t"}, creating=True)
        assert (clean, errors) == ({"name": "Atlas Copco"}, [])

    @pytest.mark.parametrize("name, ok", [("x" * 100, True), ("x" * 101, False), (" " * 3, False), (None, False),
                                          (5, False)])
    def test_name_boundaries(self, name, ok):
        _, errors = validate_manufacturer({"name": name}, creating=True)
        assert (errors == []) is ok

    def test_collapsing_counts_towards_the_limit_after_it(self):
        # 100 characters once the run of spaces is one
        assert validate_manufacturer({"name": "x" * 50 + "     " + "y" * 49}, creating=True)[1] == []

    def test_name_required_on_create_only(self):
        assert _fields(validate_manufacturer({}, creating=True)[1]) == ["name"]
        assert validate_manufacturer({"active": False}, creating=False) == ({"active": 0}, [])


class TestEquipmentModel:
    """S012 § 5.2."""

    BODY = {"manufacturer_id": 1, "designation": "GA37", "class_id": 2}

    def test_create_happy_path_with_and_without_a_type(self):
        assert validate_equipment_model(self.BODY, creating=True) == (self.BODY, [])
        clean, errors = validate_equipment_model({**self.BODY, "type_id": 4}, creating=True)
        assert errors == [] and clean["type_id"] == 4
        clean, errors = validate_equipment_model({**self.BODY, "type_id": None}, creating=True)
        assert errors == [] and clean["type_id"] is None

    def test_create_needs_manufacturer_designation_and_class(self):
        assert sorted(_fields(validate_equipment_model({}, creating=True)[1])) == [
            "class_id", "designation", "manufacturer_id"]

    def test_designation_trimmed_and_collapsed(self):
        clean, _ = validate_equipment_model({**self.BODY, "designation": "  GA 37  VSD "}, creating=True)
        assert clean["designation"] == "GA 37 VSD"

    @pytest.mark.parametrize("designation, ok", [("x" * 80, True), ("x" * 81, False), ("  ", False), (None, False)])
    def test_designation_boundaries(self, designation, ok):
        _, errors = validate_equipment_model({**self.BODY, "designation": designation}, creating=True)
        assert (errors == []) is ok
        if not ok:
            assert _fields(errors) == ["designation"]

    @pytest.mark.parametrize("field, value", [("manufacturer_id", "1"), ("manufacturer_id", 0), ("class_id", True),
                                              ("type_id", 0), ("type_id", "4")])
    def test_bad_ids(self, field, value):
        assert _fields(validate_equipment_model({**self.BODY, field: value}, creating=True)[1]) == [field]

    def test_update_leaves_absent_fields_out_and_parses_the_fixed_ones(self):
        assert validate_equipment_model({"designation": "GA55"}, creating=False) == ({"designation": "GA55"}, [])
        # Parsed so the shell can refuse a different one (fixed after create)
        assert validate_equipment_model({"class_id": 3, "type_id": None}, creating=False) == (
            {"class_id": 3, "type_id": None}, [])

    def test_label(self):
        assert model_label("Atlas Copco", "GA37") == "Atlas Copco GA37"


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


class TestTrade:

    def test_name_is_trimmed(self):
        clean, errors = validate_trade({"name": "  Fitter "}, creating=True)
        assert errors == [] and clean == {"name": "Fitter"}

    @pytest.mark.parametrize("name, ok", [("a" * 50, True), ("a" * 51, False), ("", False), ("   ", False)])
    def test_name_boundaries(self, name, ok):
        _, errors = validate_trade({"name": name}, creating=True)
        assert (errors == []) is ok
        if not ok:
            assert _fields(errors) == ["name"]

    def test_name_required_on_create_only(self):
        assert _fields(validate_trade({}, creating=True)[1]) == ["name"]
        assert validate_trade({"active": 0}, creating=False) == ({"active": 0}, [])


def _person(**overrides):
    return {"name": "Ravi", "employment": "direct", "trade_ids": [1], **overrides}


class TestPerson:

    def test_create_requires_name_and_employment_only(self):
        _, errors = validate_person({}, creating=True)
        assert set(_fields(errors)) == {"name", "employment"}

    def test_valid_create(self):
        clean, errors = validate_person(_person(name=" Ravi K ", employment="contractor"), creating=True)
        assert errors == []
        assert clean == {"name": "Ravi K", "employment": "contractor", "trade_ids": [1]}

    def test_unknown_employment(self):
        _, errors = validate_person(_person(employment="in_house"), creating=True)
        assert _fields(errors) == ["employment"]
        assert errors[0]["message"] == "Employment must be direct or contractor"

    def test_trades_absent_on_create_is_left_out(self):
        clean, errors = validate_person({"name": "Ravi", "employment": "direct"}, creating=True)
        assert errors == [] and "trade_ids" not in clean

    @pytest.mark.parametrize("creating", [True, False])
    def test_empty_trades_accepted(self, creating):
        clean, errors = validate_person(_person(trade_ids=[]), creating=creating)
        assert errors == [] and clean["trade_ids"] == []

    @pytest.mark.parametrize("bad", ["1", [1, "2"], [True], [0], None])
    def test_trade_ids_must_be_ids(self, bad):
        assert _fields(validate_person(_person(trade_ids=bad), creating=True)[1]) == ["trade_ids"]

    def test_trade_ids_deduplicated_order_kept(self):
        clean, _ = validate_person(_person(trade_ids=[3, 1, 3, 2, 1]), creating=True)
        assert clean["trade_ids"] == [3, 1, 2]

    def test_update_leaves_absent_fields_out(self):
        assert validate_person({"active": 0}, creating=False) == ({"active": 0}, [])

    @pytest.mark.parametrize("raw", [None, ""])
    def test_login_cleared(self, raw):
        clean, errors = validate_person(_person(username=raw), creating=False)
        assert errors == [] and clean["username"] is None

    def test_login_normalised(self):
        clean, errors = validate_person(_person(username="  Ravi.K "), creating=True)
        assert errors == [] and clean["username"] == "ravi.k"

    @pytest.mark.parametrize("raw", ["ravi k", "ravi/k", 5])
    def test_login_invalid(self, raw):
        assert _fields(validate_person(_person(username=raw), creating=True)[1]) == ["username"]

    def test_login_absent_on_create_is_left_out(self):
        clean, _ = validate_person(_person(), creating=True)
        assert "username" not in clean


class TestSiteRow:
    """S011 A1: one site row of a person."""

    def test_valid_rows(self):
        assert validate_site_row({"role": "maint_operator", "all_units": True}) == (
            {"role": "maint_operator", "all_units": True, "unit_ids": []}, [])
        assert validate_site_row({"role": "maint_technician", "unit_ids": [3, 2, 3]})[0]["unit_ids"] == [3, 2]

    @pytest.mark.parametrize("body, field", [
        ({}, "role"), ({"role": ""}, "role"), ({"role": "it_admin", "all_units": True}, "role"),
        ({"role": "maint_boss", "all_units": True}, "role"),
        ({"role": "maint_operator", "all_units": "yes"}, "all_units"),
        ({"role": "maint_operator", "all_units": True, "unit_ids": [1]}, "unit_ids"),
        ({"role": "maint_operator", "all_units": False}, "unit_ids"),
        ({"role": "maint_operator", "unit_ids": [True]}, "unit_ids"),
        ([1], "sites"),
    ])
    def test_refusals(self, body, field):
        assert _fields(validate_site_row(body)[1]) == [field]

    def test_missing_role_message(self):
        assert validate_site_row({"all_units": True})[1][0]["message"] == "Choose a role"


class TestSiteRows:

    def test_whole_set(self):
        rows, errors = validate_site_rows([{"site_id": 1, "role": "maint_manager", "all_units": True},
                                           {"site_id": 2, "role": "maint_operator", "unit_ids": [5]}])
        assert errors == [] and [r["site_id"] for r in rows] == [1, 2]
        assert validate_site_rows([]) == ([], [])

    @pytest.mark.parametrize("raw, field", [
        ("x", "sites"), ({}, "sites"), ([1], "sites"), ([{"role": "maint_operator", "all_units": True}], "site_id"),
        ([{"site_id": 0, "role": "maint_operator", "all_units": True}], "site_id"),
        ([{"site_id": True, "role": "maint_operator", "all_units": True}], "site_id"),
        ([{"site_id": 1, "role": "maint_operator", "all_units": True},
          {"site_id": 1, "role": "maint_manager", "all_units": True}], "sites"),
    ])
    def test_refusals(self, raw, field):
        assert _fields(validate_site_rows(raw)[1]) == [field]


class TestEngineerLimits:

    def test_no_login_only_technician(self):
        assert no_login_role_error(["maint_technician", "maint_technician"]) is None
        assert no_login_role_error([]) is None
        assert no_login_role_error(["maint_technician", "maint_operator"]) == NO_LOGIN_ROLE_MESSAGE

    @pytest.mark.parametrize("stored, new, ok", [
        (None, "maint_technician", True), ("maint_technician", "maint_technician", True),
        ("maint_technician", None, True), (None, None, True),
        ("maint_operator", "maint_technician", False), (None, "maint_supervisor", False),
        ("maint_technician", "maint_engineer", False),
    ])
    def test_technician_only(self, stored, new, ok):
        assert technician_only(stored, new) is ok
