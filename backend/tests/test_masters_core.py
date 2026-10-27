"""Pure validation of the masters' input — no DB, no Flask."""

import pytest

from masters_core import (
    CAUSE_GROUPS, NO_LOGIN_ROLE_MESSAGE, category_in_use, model_label, no_login_role_error, normalise_username,
    technician_only, validate_equipment_category, validate_equipment_class, validate_equipment_model,
    validate_failure_cause, validate_failure_mode, validate_maintenance_action, validate_equipment_type, validate_manufacturer, validate_meter_type,
    validate_person, validate_site, validate_site_row, validate_site_rows, validate_trade, validate_unit,
    optional_text_parser, validate_unit_ids, validate_username,
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


class TestEquipmentCategory:
    """S063 § 5.1, § 5.2: the category's name and the class's optional category."""

    @pytest.mark.parametrize("name, ok", [("", False), ("  ", False), ("x", True), ("x" * 50, True),
                                          ("x" * 51, False), (None, False), (5, False)])
    def test_name_boundaries(self, name, ok):
        clean, errors = validate_equipment_category({"name": name}, creating=True)
        assert (errors == []) is ok
        if not ok:
            assert _fields(errors) == ["name"]

    def test_name_is_trimmed_and_active_is_optional(self):
        assert validate_equipment_category({"name": " Lifting equipment "}, creating=True) == (
            {"name": "Lifting equipment"}, [])
        assert validate_equipment_category({"active": False}, creating=False) == ({"active": 0}, [])

    @pytest.mark.parametrize("value, ok", [(None, True), (1, True), (0, False), (-2, False), (True, False),
                                           ("3", False), (2.0, False)])
    def test_class_category_id(self, value, ok):
        clean, errors = validate_equipment_class({"category_id": value}, creating=False)
        if ok:
            assert (clean, errors) == ({"category_id": value}, [])
        else:
            assert errors == [{"field": "category_id", "message": "Category must be a record id"}]

    def test_class_category_is_not_required(self):
        clean, errors = validate_equipment_class({"code": "VBM", "name": "Mill"}, creating=True)
        assert errors == [] and "category_id" not in clean

    def test_category_in_use_message(self):
        assert category_in_use(1) == "1 active class is in this category. Move it to another category first."
        assert category_in_use(3) == "3 active classes are in this category. Move them to another category first."


class TestEquipmentType:

    def test_create_happy_path(self):
        clean, errors = validate_equipment_type({"class_id": 3, "name": "  Closed execution "}, creating=True)
        assert errors == []
        assert clean == {"class_id": 3, "name": "Closed execution"}

    def test_create_needs_class_and_name(self):
        _, errors = validate_equipment_type({}, creating=True)
        assert sorted(_fields(errors)) == ["class_id", "name"]

    def test_a_missing_or_bad_class_reads_as_a_choice(self):
        # S064 UX-13 row 20: a record select says what to do, sent or not; other fields keep theirs
        _, errors = validate_equipment_type({}, creating=True)
        assert {"field": "class_id", "message": "Choose a class."} in errors
        assert {"field": "name", "message": "Name is required"} in errors
        assert validate_equipment_type({"class_id": None, "name": "x"}, creating=True)[1] == [
            {"field": "class_id", "message": "Choose a class."}]
        _, errors = validate_equipment_model({}, creating=True)
        assert {"field": "manufacturer_id", "message": "Choose a manufacturer."} in errors

    def test_reserved_name_says_what_to_do(self):
        _, errors = validate_equipment_type({"class_id": 3, "name": "none"}, creating=True)
        assert errors == [{"field": "name", "message": 'Choose another name; "none" is reserved.'}]

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


class TestOptionalTextParser:
    def test_default_only_strips_so_inner_spaces_stay(self):
        assert optional_text_parser("Note", 20)("  a   b ") == "a   b"

    def test_collapse_joins_inner_runs_of_spaces(self):
        assert optional_text_parser("Note", 20, collapse=True)("  a   b ") == "a b"

    def test_collapse_keeps_empty_null_text_and_length_rules(self):
        parse = optional_text_parser("Note", 3, collapse=True)
        assert parse("   ") is None and parse(None) is None
        assert parse("a  b") == "a b"
        with pytest.raises(ValueError, match="Note must be text"):
            parse(5)
        with pytest.raises(ValueError, match="Note must be at most 3 characters"):
            parse("abcd")


class TestMeterType:

    @staticmethod
    def _gauge(**overrides):
        return {"name": "Oil temperature", "unit": "°C", "kind": "gauge", **overrides}

    @staticmethod
    def _yes_no(**overrides):
        return {"name": "Oil level above min", "kind": "yes_no", "expected_answer": "yes", **overrides}

    @pytest.mark.parametrize("kind", ["counter", "gauge", "amount"])
    def test_measured_kinds_need_a_unit(self, kind):
        clean, errors = validate_meter_type({"name": "X", "unit": "h", "kind": kind}, creating=True)
        assert errors == [] and clean == {"name": "X", "unit": "h", "kind": kind}

    def test_decimals_absent_on_create_is_left_out(self):
        clean, errors = validate_meter_type(self._gauge(), creating=True)
        assert errors == [] and "decimals" not in clean

    def test_name_and_unit_are_trimmed_collapsed_and_keep_their_case(self):
        clean, errors = validate_meter_type(self._gauge(name="  Oil   temperature ", unit=" kWh "), creating=True)
        assert errors == [] and (clean["name"], clean["unit"]) == ("Oil temperature", "kWh")

    @pytest.mark.parametrize("name, ok", [("a" * 60, True), ("a" * 61, False), ("", False), ("   ", False)])
    def test_name_boundaries(self, name, ok):
        _, errors = validate_meter_type(self._gauge(name=name), creating=True)
        assert (errors == []) is ok
        if not ok:
            assert _fields(errors) == ["name"]

    def test_name_missing_on_create(self):
        _, errors = validate_meter_type({"unit": "h", "kind": "counter"}, creating=True)
        assert errors == [{"field": "name", "message": "Name is required"}]

    @pytest.mark.parametrize("unit, ok", [("u" * 20, True), ("u" * 21, False)])
    def test_unit_boundaries(self, unit, ok):
        _, errors = validate_meter_type(self._gauge(unit=unit), creating=True)
        assert (errors == []) is ok
        if not ok:
            assert errors == [{"field": "unit", "message": "Unit must be at most 20 characters"}]

    @pytest.mark.parametrize("unit", [None, "", "   "])
    def test_unit_missing_or_empty_for_a_measured_kind(self, unit):
        _, errors = validate_meter_type(self._gauge(unit=unit), creating=True)
        assert errors == [{"field": "unit", "message": "Unit is required"}]

    def test_unit_absent_on_create_for_a_measured_kind(self):
        _, errors = validate_meter_type({"name": "X", "kind": "gauge"}, creating=True)
        assert errors == [{"field": "unit", "message": "Unit is required"}]

    def test_kind_missing_on_create_and_unknown(self):
        assert validate_meter_type({"name": "X", "unit": "h"}, creating=True)[1] == [
            {"field": "kind", "message": "Kind is required"}]
        assert validate_meter_type(self._gauge(kind="dial"), creating=True)[1] == [
            {"field": "kind", "message": "Kind must be one of: counter, gauge, amount, yes_no"}]

    def test_a_yes_no_type_has_an_expected_answer_and_no_unit_or_decimals(self):
        clean, errors = validate_meter_type(self._yes_no(unit=None, decimals=0), creating=True)
        assert errors == [] and clean["expected_answer"] == "yes" and clean["unit"] is None

    @pytest.mark.parametrize("overrides, field, message", [
        ({"unit": "h"}, "unit", "A Yes / No meter type has no unit"),
        ({"expected_answer": None}, "expected_answer", "Expected answer is required"),
        ({"expected_answer": ""}, "expected_answer", "Expected answer is required"),
        ({"expected_answer": "maybe"}, "expected_answer", "Expected answer must be one of: yes, no"),
        ({"decimals": 1}, "decimals", "A Yes / No meter type has no decimals"),
    ])
    def test_yes_no_refusals(self, overrides, field, message):
        _, errors = validate_meter_type(self._yes_no(**overrides), creating=True)
        assert errors == [{"field": field, "message": message}]

    def test_an_expected_answer_on_a_gauge_is_refused(self):
        _, errors = validate_meter_type(self._gauge(expected_answer="yes"), creating=True)
        assert errors == [{"field": "expected_answer", "message": "Only a Yes / No meter type has an expected answer"}]

    @pytest.mark.parametrize("raw", [True, 1.0, "1", -1, 4, None])
    def test_decimals_must_be_a_whole_number_from_0_to_3(self, raw):
        _, errors = validate_meter_type(self._gauge(decimals=raw), creating=True)
        assert errors == [{"field": "decimals", "message": "Decimals must be a whole number from 0 to 3"}]

    @pytest.mark.parametrize("raw", [0, 1, 2, 3])
    def test_decimals_accepted(self, raw):
        assert validate_meter_type(self._gauge(decimals=raw), creating=True)[0]["decimals"] == raw

    def test_active_must_be_a_bool(self):
        assert _fields(validate_meter_type(self._gauge(active="yes"), creating=True)[1]) == ["active"]

    def test_unknown_keys_are_ignored(self):
        clean, _ = validate_meter_type(self._gauge(colour="red"), creating=True)
        assert "colour" not in clean

    GAUGE_ROW = {"name": "Oil temperature", "unit": "°C", "kind": "gauge", "expected_answer": None, "decimals": 1}

    def test_put_without_a_field_leaves_it_alone(self):
        assert validate_meter_type({"active": 0}, creating=False, stored=self.GAUGE_ROW) == ({"active": 0}, [])

    def test_put_gauge_to_yes_no_without_the_expected_answer_is_refused(self):
        # The stored unit and decimals are still there, so those are refused too; the first
        # error the route reports is the unit
        _, errors = validate_meter_type({"kind": "yes_no"}, creating=False, stored=self.GAUGE_ROW)
        assert _fields(errors) == ["unit", "expected_answer", "decimals"]

    def test_put_gauge_to_yes_no_with_the_whole_shape_is_accepted(self):
        body = {"kind": "yes_no", "unit": None, "expected_answer": "no", "decimals": 0}
        assert validate_meter_type(body, creating=False, stored=self.GAUGE_ROW)[1] == []

    def test_put_yes_no_to_gauge_needs_a_unit_and_drops_the_answer(self):
        stored = {"name": "Q", "unit": None, "kind": "yes_no", "expected_answer": "yes", "decimals": 0}
        _, errors = validate_meter_type({"kind": "gauge"}, creating=False, stored=stored)
        assert _fields(errors) == ["unit", "expected_answer"]
        body = {"kind": "gauge", "unit": "°C", "expected_answer": None}
        assert validate_meter_type(body, creating=False, stored=stored)[1] == []


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

    def test_no_login_technician_or_operator(self):
        """S017 user decision 5: an Operator row without a login is accepted too."""
        assert no_login_role_error(["maint_technician", "maint_technician"]) is None
        assert no_login_role_error([]) is None
        assert no_login_role_error(["maint_technician", "maint_operator"]) is None
        assert no_login_role_error(["maint_operator"]) is None
        assert NO_LOGIN_ROLE_MESSAGE == "Without a login, a person can only be a technician or an operator"

    @pytest.mark.parametrize("role", ["maint_supervisor", "maint_engineer", "maint_manager", "maint_storekeeper"])
    def test_no_login_other_roles_refused(self, role):
        assert no_login_role_error(["maint_technician", role]) == NO_LOGIN_ROLE_MESSAGE

    @pytest.mark.parametrize("stored, new, ok", [
        (None, "maint_technician", True), ("maint_technician", "maint_technician", True),
        ("maint_technician", None, True), (None, None, True),
        ("maint_operator", "maint_technician", False), (None, "maint_supervisor", False),
        ("maint_technician", "maint_engineer", False),
    ])
    def test_technician_only(self, stored, new, ok):
        assert technician_only(stored, new) is ok


# ---------------------------------------------------------------------------
# Failure codes (S016 § 5.1–5.3)
# ---------------------------------------------------------------------------

_FAILURE_VALIDATORS = [
    (validate_failure_mode, {}),
    (validate_failure_cause, {"cause_group": "operation"}),
    (validate_maintenance_action, {}),
]


class TestFailureCode:

    @pytest.mark.parametrize("validate, extra", _FAILURE_VALIDATORS)
    @pytest.mark.parametrize("code, expected", [
        ("3.4", "3.4"), ("NOI", "NOI"), ("12", "12"), (" noi ", "NOI"), ("a.b.c", "A.B.C"),
        ("ABCDEFGH", "ABCDEFGH"), ("1", "1"),
    ])
    def test_accepted_upper_cased_and_trimmed(self, validate, extra, code, expected):
        clean, errors = validate({"code": code, "label": "Noise", **extra}, creating=True)
        assert errors == []
        assert clean["code"] == expected

    @pytest.mark.parametrize("validate, extra", _FAILURE_VALIDATORS)
    @pytest.mark.parametrize("code", ["", "   ", "ABCDEFGHI", ".4", "3.", "1..2", "N OI", "N-OI", "1/2", None, 12])
    def test_refused(self, validate, extra, code):
        _, errors = validate({"code": code, "label": "Noise", **extra}, creating=True)
        assert _fields(errors) == ["code"]

    def test_refusal_text_shows_the_form(self):
        # S064 UX-13 row 15
        _, errors = validate_failure_cause({"code": "N-OI", "label": "Noise", "cause_group": "design"},
                                           creating=True)
        assert errors[0]["message"] == "Use up to 8 letters or digits, parts joined by a dot, e.g. NOI or 3.4."


class TestFailureLabelAndDescription:

    @pytest.mark.parametrize("validate, extra", _FAILURE_VALIDATORS)
    def test_label_collapsed(self, validate, extra):
        clean, errors = validate({"code": "X", "label": "  Not   building  pressure ", **extra}, creating=True)
        assert errors == [] and clean["label"] == "Not building pressure"

    @pytest.mark.parametrize("validate, extra", _FAILURE_VALIDATORS)
    @pytest.mark.parametrize("label, ok", [("a" * 60, True), ("a" * 61, False), ("", False), ("  ", False),
                                           (None, False)])
    def test_label_boundaries(self, validate, extra, label, ok):
        _, errors = validate({"code": "X", "label": label, **extra}, creating=True)
        assert (errors == []) is ok
        if not ok:
            assert _fields(errors) == ["label"]

    @pytest.mark.parametrize("validate, extra", _FAILURE_VALIDATORS)
    def test_code_and_label_required_on_create_only(self, validate, extra):
        assert _fields(validate({**extra}, creating=True)[1]) == ["code", "label"]
        assert validate({"active": False}, creating=False) == ({"active": 0}, [])

    @pytest.mark.parametrize("validate, extra", _FAILURE_VALIDATORS)
    @pytest.mark.parametrize("raw, expected", [("  Noise ", "Noise"), ("", None), ("   ", None), (None, None),
                                               ("a" * 255, "a" * 255)])
    def test_description_optional(self, validate, extra, raw, expected):
        clean, errors = validate({"code": "X", "label": "L", "description": raw, **extra}, creating=True)
        assert errors == [] and clean["description"] == expected

    @pytest.mark.parametrize("validate, extra", _FAILURE_VALIDATORS)
    @pytest.mark.parametrize("raw", ["a" * 256, 5])
    def test_description_refused(self, validate, extra, raw):
        _, errors = validate({"code": "X", "label": "L", "description": raw, **extra}, creating=True)
        assert _fields(errors) == ["description"]

    @pytest.mark.parametrize("validate, extra", _FAILURE_VALIDATORS)
    def test_description_absent_is_left_out(self, validate, extra):
        clean, errors = validate({"code": "X", "label": "L", **extra}, creating=True)
        assert errors == [] and "description" not in clean


class TestFailureMode:

    def test_class_optional_or_null(self):
        assert validate_failure_mode({"code": "NOI", "label": "Noise"}, creating=True) == (
            {"code": "NOI", "label": "Noise"}, [])
        clean, errors = validate_failure_mode({"code": "NOI", "label": "Noise", "class_id": None}, creating=True)
        assert errors == [] and clean["class_id"] is None
        clean, errors = validate_failure_mode({"code": "NOI", "label": "Noise", "class_id": 4}, creating=True)
        assert errors == [] and clean["class_id"] == 4

    @pytest.mark.parametrize("raw", [0, -1, "4", True, 1.5])
    def test_class_must_be_an_id(self, raw):
        _, errors = validate_failure_mode({"code": "NOI", "label": "Noise", "class_id": raw}, creating=True)
        assert _fields(errors) == ["class_id"]


class TestFailureCause:

    def test_groups_are_isos_five(self):
        assert CAUSE_GROUPS == ("design", "fabrication", "operation", "management", "misc")

    @pytest.mark.parametrize("group", CAUSE_GROUPS)
    def test_each_group_accepted(self, group):
        clean, errors = validate_failure_cause({"code": "3.4", "label": "Wear", "cause_group": group}, creating=True)
        assert errors == [] and clean["cause_group"] == group

    def test_group_required_on_create(self):
        _, errors = validate_failure_cause({"code": "3.4", "label": "Wear"}, creating=True)
        assert _fields(errors) == ["cause_group"]

    @pytest.mark.parametrize("raw", ["", "Design", "other", None, 1])
    def test_unknown_group_refused(self, raw):
        _, errors = validate_failure_cause({"code": "3.4", "label": "Wear", "cause_group": raw}, creating=True)
        assert _fields(errors) == ["cause_group"]

    def test_group_may_change_on_update(self):
        assert validate_failure_cause({"cause_group": "misc"}, creating=False) == ({"cause_group": "misc"}, [])


class TestMaintenanceAction:

    def test_has_no_class_or_group(self):
        clean, errors = validate_maintenance_action(
            {"code": "1", "label": "Replace", "class_id": 3, "cause_group": "misc"}, creating=True)
        assert errors == [] and clean == {"code": "1", "label": "Replace"}
