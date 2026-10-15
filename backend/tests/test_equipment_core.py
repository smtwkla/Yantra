"""Equipment register — pure rules (no DB, no Flask)."""

import pytest

from equipment_core import (
    check_parent, check_status_change, check_type_class, effective_criticality, format_equipment_code,
    full_path, tracked_changes, validate_equipment,
)

THIS_YEAR = 2026


def _fields(errors):
    return [e["field"] for e in errors]


def _create(**data):
    return validate_equipment(data, creating=True, this_year=THIS_YEAR)


def _update(stored_level="equipment", stored_code="VBM001", **data):
    return validate_equipment(data, creating=False, this_year=THIS_YEAR,
                              stored={"code": stored_code, "level": stored_level})


EQUIPMENT = {"level": "equipment", "unit_id": 1, "class_id": 2, "name": "Vertical blade mill"}
PART = {"level": "component", "parent_id": 5, "class_id": 2, "name": "Motor"}


class TestFormatCode:

    @pytest.mark.parametrize("number, code", [
        (1, "VBM001"), (999, "VBM999"), (1000, "VBM1000"), (10000, "VBM10000"),
    ])
    def test_zero_padded_to_three(self, number, code):
        assert format_equipment_code("VBM", number) == code


class TestCheckParent:

    @pytest.mark.parametrize("child, parent, ok", [
        ("equipment", None, True),
        ("equipment", "equipment", False),
        ("equipment", "component_unit", False),
        ("equipment", "component", False),
        ("component_unit", None, False),
        ("component_unit", "equipment", True),
        ("component_unit", "component_unit", False),
        ("component_unit", "component", False),
        ("component", None, False),
        ("component", "equipment", True),
        ("component", "component_unit", True),
        ("component", "component", False),
    ])
    def test_level_table(self, child, parent, ok):
        assert (check_parent(child, parent) is None) is ok


class TestEffectiveCriticality:

    @pytest.mark.parametrize("own, root, effective", [
        (None, "A", "A"), ("B", "A", "B"), ("C", "C", "C"), (None, None, None),
    ])
    def test_own_grade_wins_else_inherit(self, own, root, effective):
        assert effective_criticality(own, root) == effective


class TestFullPath:

    @pytest.mark.parametrize("codes, path", [
        (["VBM001"], "SMTW.FWMILL.VBM001"),
        (["VBM001", "DRV002"], "SMTW.FWMILL.VBM001.DRV002"),
        (["VBM001", "DRV002", "MOT017"], "SMTW.FWMILL.VBM001.DRV002.MOT017"),
    ])
    def test_each_depth(self, codes, path):
        assert full_path("SMTW", "FWMILL", codes) == path


class TestCheckTypeClass:

    def test_match(self):
        assert check_type_class(4, 4) is None

    def test_mismatch(self):
        assert check_type_class(4, 5) == "This type belongs to another class"


def _state(**overrides):
    base = {"level": "equipment", "full_path": "S.U.VBM001", "class_code": "VBM", "type_name": None,
            "criticality": "C", "status": "in_service", "name": "Mill", "make": "X", "year": 2020,
            "notes": None}
    return {**base, **overrides}


class TestTrackedChanges:

    def test_no_change(self):
        assert tracked_changes(_state(), _state()) == []

    def test_untracked_fields_give_no_event(self):
        assert tracked_changes(_state(), _state(name="Mill 2", make="Y", year=2021)) == []

    @pytest.mark.parametrize("field, old, new, event", [
        ("class_code", "VBM", "HP", "class"),
        ("criticality", "C", "A", "criticality"),
        ("status", "in_service", "standby", "status"),
    ])
    def test_each_tracked_field(self, field, old, new, event):
        assert tracked_changes(_state(**{field: old}), _state(**{field: new})) == [(event, old, new)]

    def test_equipment_path_change_is_moved_unit(self):
        before, after = _state(full_path="S.U1.VBM001"), _state(full_path="S.U2.VBM001")
        assert tracked_changes(before, after) == [("moved_unit", "S.U1.VBM001", "S.U2.VBM001")]

    @pytest.mark.parametrize("level", ["component_unit", "component"])
    def test_part_path_change_is_moved_parent(self, level):
        before = _state(level=level, full_path="S.U1.BRK001.MOT001")
        after = _state(level=level, full_path="S.U2.BRK002.MOT001")
        assert tracked_changes(before, after) == [("moved_parent", "S.U1.BRK001.MOT001", "S.U2.BRK002.MOT001")]

    def test_criticality_inherit_to_a(self):
        before, after = _state(level="component", criticality=None), _state(level="component", criticality="A")
        assert tracked_changes(before, after) == [("criticality", "inherit", "A")]

    def test_criticality_back_to_inherit(self):
        before, after = _state(level="component", criticality="B"), _state(level="component", criticality=None)
        assert tracked_changes(before, after) == [("criticality", "B", "inherit")]

    def test_type_set(self):
        assert tracked_changes(_state(), _state(type_name="Closed execution")) == [
            ("type", "none", "Closed execution")]

    def test_type_changed(self):
        before, after = _state(type_name="Closed execution"), _state(type_name="Open execution")
        assert tracked_changes(before, after) == [("type", "Closed execution", "Open execution")]

    def test_type_cleared(self):
        assert tracked_changes(_state(type_name="Closed execution"), _state()) == [
            ("type", "Closed execution", "none")]

    def test_same_type_name_across_a_class_change_is_a_class_event_only(self):
        before = _state(class_code="RPP", type_name="Standard")
        after = _state(class_code="HP", type_name="Standard")
        assert tracked_changes(before, after) == [("class", "RPP", "HP")]

    def test_notes_change_gives_no_event(self):
        assert tracked_changes(_state(), _state(notes="Mounted on the\nleft side")) == []

    def test_several_changes_one_event_each(self):
        events = tracked_changes(_state(), _state(class_code="HP", status="scrapped", name="x"))
        assert sorted(e[0] for e in events) == ["class", "status"]


class TestCheckStatusChange:

    @pytest.mark.parametrize("old, new, ok", [
        (None, "in_service", True), (None, "standby", True), (None, "out_of_use", True), (None, "scrapped", False),
        ("in_service", "standby", True), ("in_service", "out_of_use", True), ("in_service", "scrapped", True),
        ("standby", "in_service", True), ("standby", "out_of_use", True), ("standby", "scrapped", True),
        ("out_of_use", "in_service", True), ("out_of_use", "standby", True), ("out_of_use", "scrapped", True),
        ("scrapped", "in_service", False), ("scrapped", "standby", False), ("scrapped", "out_of_use", False),
        ("scrapped", "scrapped", True), ("in_service", "in_service", True),
    ])
    def test_table(self, old, new, ok):
        assert (check_status_change(old, new) is None) is ok


class TestValidateCreate:

    def test_equipment_happy_path_defaults_criticality_c(self):
        clean, errors = _create(**EQUIPMENT, make="  Kirloskar ", serial_no="")
        assert errors == []
        assert clean == {"level": "equipment", "unit_id": 1, "class_id": 2, "name": "Vertical blade mill",
                         "make": "Kirloskar", "serial_no": None, "criticality": "C"}

    def test_part_happy_path_inherits(self):
        clean, errors = _create(**PART)
        assert errors == []
        assert clean == {"level": "component", "parent_id": 5, "class_id": 2, "name": "Motor"}

    @pytest.mark.parametrize("level, missing", [
        ("equipment", ["class_id", "name", "unit_id"]),
        ("component_unit", ["class_id", "name", "parent_id"]),
        ("component", ["class_id", "name", "parent_id"]),
    ])
    def test_required_fields_per_level(self, level, missing):
        _, errors = _create(level=level)
        assert sorted(_fields(errors)) == missing

    def test_level_is_required_and_an_enum(self):
        assert _fields(_create(class_id=1, name="x")[1]) == ["level"]
        assert _fields(_create(level="assembly", class_id=1, name="x")[1]) == ["level"]

    def test_unit_on_a_part_is_400(self):
        _, errors = _create(**PART, unit_id=1)
        assert _fields(errors) == ["unit_id"]

    def test_parent_on_equipment_is_400(self):
        _, errors = _create(**EQUIPMENT, parent_id=3)
        assert _fields(errors) == ["parent_id"]

    def test_null_parent_on_equipment_is_fine(self):
        clean, errors = _create(**EQUIPMENT, parent_id=None)
        assert errors == [] and "parent_id" not in clean

    def test_code_in_body_is_ignored_on_create(self):
        clean, errors = _create(**EQUIPMENT, code="ZZZ999")
        assert errors == [] and "code" not in clean

    @pytest.mark.parametrize("field, value", [
        ("status", "broken"), ("criticality", "D"), ("criticality", "a"), ("class_id", "2"),
        ("class_id", True), ("unit_id", 0), ("make", 5), ("make", "x" * 101), ("name", "  "),
    ])
    def test_bad_values(self, field, value):
        _, errors = _create(**{**EQUIPMENT, field: value})
        assert _fields(errors) == [field]

    @pytest.mark.parametrize("status", ["in_service", "standby", "out_of_use"])
    def test_born_status(self, status):
        assert _create(**EQUIPMENT, status=status)[1] == []

    def test_born_scrapped_is_400(self):
        _, errors = _create(**EQUIPMENT, status="scrapped")
        assert _fields(errors) == ["status"]

    @pytest.mark.parametrize("year, ok", [
        (1899, False), (1900, True), (THIS_YEAR, True), (THIS_YEAR + 1, True), (THIS_YEAR + 2, False),
        ("2020", False), (True, False), (None, True),
    ])
    def test_year_bounds(self, year, ok):
        _, errors = _create(**EQUIPMENT, year=year)
        assert (errors == []) is ok

    def test_null_criticality_on_equipment_is_400(self):
        _, errors = _create(**EQUIPMENT, criticality=None)
        assert _fields(errors) == ["criticality"]

    def test_null_criticality_on_a_part_means_inherit(self):
        clean, errors = _create(**PART, criticality=None)
        assert errors == [] and clean["criticality"] is None


class TestTypeAndNotes:

    def test_type_id_is_an_id(self):
        clean, errors = _create(**EQUIPMENT, type_id=7)
        assert errors == [] and clean["type_id"] == 7

    @pytest.mark.parametrize("type_id", [0, "7", True, 1.5])
    def test_bad_type_id(self, type_id):
        assert _fields(_create(**EQUIPMENT, type_id=type_id)[1]) == ["type_id"]

    def test_null_type_is_dropped_on_create(self):
        clean, errors = _create(**EQUIPMENT, type_id=None)
        assert errors == [] and "type_id" not in clean

    def test_null_type_is_kept_on_update(self):
        assert _update(type_id=None) == ({"type_id": None}, [])

    @pytest.mark.parametrize("raw", ["", "   ", "\n \n", None])
    def test_empty_notes_become_null(self, raw):
        clean, errors = _create(**EQUIPMENT, notes=raw)
        assert errors == [] and clean["notes"] is None

    def test_notes_trimmed_with_inner_line_breaks_kept(self):
        clean, _ = _create(**EQUIPMENT, notes="  Mounted on the left\n\n  Manual: shelf 3  \n")
        assert clean["notes"] == "Mounted on the left\n\n  Manual: shelf 3"

    def test_notes_of_2000_characters_are_fine(self):
        assert _create(**EQUIPMENT, notes="x" * 2000)[1] == []

    @pytest.mark.parametrize("raw", ["x" * 2001, 5])
    def test_bad_notes(self, raw):
        assert _fields(_create(**EQUIPMENT, notes=raw)[1]) == ["notes"]


class TestValidateUpdate:

    def test_absent_fields_are_unchanged(self):
        assert _update(name="New") == ({"name": "New"}, [])

    def test_nothing_is_required(self):
        assert _update() == ({}, [])

    def test_unchanged_code_and_level_are_accepted_and_dropped(self):
        assert _update(code="vbm001 ", level="equipment", name="x") == ({"name": "x"}, [])

    @pytest.mark.parametrize("field, value", [("code", "VBM002"), ("code", 5), ("level", "component")])
    def test_changed_code_or_level_is_400(self, field, value):
        _, errors = _update(**{field: value})
        assert _fields(errors) == [field]

    def test_null_criticality_on_equipment_is_400(self):
        assert _fields(_update(criticality=None)[1]) == ["criticality"]

    def test_null_criticality_on_a_part_reinherits(self):
        assert _update(stored_level="component", criticality=None) == ({"criticality": None}, [])

    def test_equipment_cannot_lose_its_unit_or_gain_a_parent(self):
        assert _fields(_update(unit_id=None)[1]) == ["unit_id"]
        assert _fields(_update(parent_id=4)[1]) == ["parent_id"]

    def test_part_cannot_gain_a_unit_or_lose_its_parent(self):
        assert _fields(_update(stored_level="component_unit", unit_id=4)[1]) == ["unit_id"]
        assert _fields(_update(stored_level="component_unit", parent_id=None)[1]) == ["parent_id"]

    def test_move_fields_by_level(self):
        assert _update(unit_id=7) == ({"unit_id": 7}, [])
        assert _update(stored_level="component", parent_id=7) == ({"parent_id": 7}, [])

    def test_scrapped_is_a_valid_target_status_on_update(self):
        assert _update(status="scrapped") == ({"status": "scrapped"}, [])
