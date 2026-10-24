"""Equipment register — pure rules (no DB, no Flask)."""

import pytest

from equipment_core import (
    CLASS_FROM_MODEL, MODEL_INACTIVE, NO_MODEL, PICK_A_CLASS, PICK_A_MODEL, PICK_A_TYPE, PICK_A_TYPE_OF_CLASS,
    TYPE_FROM_MODEL, check_lifecycle_change, check_parent, check_type_class, derive_from_model,
    effective_criticality, format_equipment_code, full_path, tracked_changes, validate_equipment,
)

THIS_YEAR = 2026


def _fields(errors):
    return [e["field"] for e in errors]


def _create(**data):
    return validate_equipment(data, creating=True, this_year=THIS_YEAR)


def _update(stored_level="equipment", stored_code="VBM001", stored_model_id=2, stored_class_id=1,
            stored_type_id=None, **data):
    return validate_equipment(data, creating=False, this_year=THIS_YEAR,
                              stored={"code": stored_code, "level": stored_level, "model_id": stored_model_id,
                                      "class_id": stored_class_id, "type_id": stored_type_id})


EQUIPMENT = {"level": "equipment", "unit_id": 1, "model_id": 2, "name": "Vertical blade mill"}
PART = {"level": "component", "parent_id": 5, "model_id": 2, "name": "Motor"}


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


class TestDeriveFromModel:
    """S012 § 5.3: the class and type come from the model."""

    GA37 = {"id": 7, "class_id": 3, "type_id": 11, "active": 1}

    def test_create_takes_class_and_type_from_the_model(self):
        assert derive_from_model(None, self.GA37) == (3, 11, None)

    def test_a_model_without_a_type_gives_none(self):
        assert derive_from_model(None, {**self.GA37, "type_id": None}) == (3, None, None)

    def test_a_newly_picked_inactive_model_is_refused(self):
        inactive = {**self.GA37, "active": 0}
        assert derive_from_model(None, inactive)[2] == MODEL_INACTIVE == "This model is inactive"
        assert derive_from_model(5, inactive)[2] == MODEL_INACTIVE

    def test_an_unchanged_inactive_model_is_kept(self):
        assert derive_from_model(7, {**self.GA37, "active": 0}) == (3, 11, None)

    def test_a_model_whose_type_is_inactive_can_be_picked(self):
        # The model row carries no type state: the model's own flag decides (BR1-06)
        assert derive_from_model(None, self.GA37)[2] is None


def _state(**overrides):
    base = {"level": "equipment", "full_path": "S.U.VBM001", "model_label": "Atlas Copco GA37", "class_code": "VBM",
            "type_name": None, "criticality": "C", "lifecycle": "in_service", "name": "Mill", "serial_no": "X",
            "year": 2020, "notes": None}
    return {**base, **overrides}


class TestTrackedChanges:

    def test_no_change(self):
        assert tracked_changes(_state(), _state()) == []

    def test_untracked_fields_give_no_event(self):
        assert tracked_changes(_state(), _state(name="Mill 2", serial_no="Y", year=2021)) == []

    @pytest.mark.parametrize("field, old, new, event", [
        ("model_label", "Atlas Copco GA37", "Atlas Copco GA55", "model"),
        ("class_code", "VBM", "HP", "class"),
        ("criticality", "C", "A", "criticality"),
        ("lifecycle", "in_service", "standby", "lifecycle"),
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

    def test_a_model_of_another_class_and_type_gives_three_events(self):
        before = _state(model_label="Atlas Copco GA37", class_code="CMP", type_name="Screw compressor")
        after = _state(model_label="Haendle VAH-600", class_code="EXT", type_name=None)
        assert tracked_changes(before, after) == [
            ("model", "Atlas Copco GA37", "Haendle VAH-600"), ("class", "CMP", "EXT"),
            ("type", "Screw compressor", "none")]

    def test_notes_change_gives_no_event(self):
        assert tracked_changes(_state(), _state(notes="Mounted on the\nleft side")) == []

    def test_several_changes_one_event_each(self):
        events = tracked_changes(_state(), _state(class_code="HP", lifecycle="scrapped", name="x"))
        assert sorted(e[0] for e in events) == ["class", "lifecycle"]


class TestCheckLifecycleChange:

    @pytest.mark.parametrize("old, new, ok", [
        (None, "in_service", True), (None, "standby", True), (None, "out_of_use", True), (None, "scrapped", False),
        ("in_service", "standby", True), ("in_service", "out_of_use", True), ("in_service", "scrapped", True),
        ("standby", "in_service", True), ("standby", "out_of_use", True), ("standby", "scrapped", True),
        ("out_of_use", "in_service", True), ("out_of_use", "standby", True), ("out_of_use", "scrapped", True),
        ("scrapped", "in_service", False), ("scrapped", "standby", False), ("scrapped", "out_of_use", False),
        ("scrapped", "scrapped", True), ("in_service", "in_service", True),
    ])
    def test_table(self, old, new, ok):
        assert (check_lifecycle_change(old, new) is None) is ok


class TestValidateCreate:

    def test_equipment_happy_path_defaults_criticality_c(self):
        clean, errors = _create(**EQUIPMENT, serial_no="")
        assert errors == []
        assert clean == {"level": "equipment", "unit_id": 1, "model_id": 2, "name": "Vertical blade mill",
                         "serial_no": None, "criticality": "C"}

    def test_part_happy_path_inherits(self):
        clean, errors = _create(**PART)
        assert errors == []
        assert clean == {"level": "component", "parent_id": 5, "model_id": 2, "name": "Motor"}

    @pytest.mark.parametrize("level, missing", [
        ("equipment", ["model_id", "name", "unit_id"]),
        ("component_unit", ["model_id", "name", "parent_id"]),
        ("component", ["model_id", "name", "parent_id"]),
    ])
    def test_required_fields_per_level(self, level, missing):
        _, errors = _create(level=level)
        assert sorted(_fields(errors)) == missing

    def test_level_is_required_and_an_enum(self):
        assert _fields(_create(model_id=1, name="x")[1]) == ["level"]
        assert _fields(_create(level="assembly", model_id=1, name="x")[1]) == ["level"]

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
        ("lifecycle", "broken"), ("criticality", "D"), ("criticality", "a"), ("model_id", "2"),
        ("model_id", True), ("model_id", 0), ("unit_id", 0), ("serial_no", 5), ("serial_no", "x" * 101),
        ("name", "  "),
    ])
    def test_bad_values(self, field, value):
        _, errors = _create(**{**EQUIPMENT, field: value})
        assert _fields(errors) == [field]

    @pytest.mark.parametrize("lifecycle", ["in_service", "standby", "out_of_use"])
    def test_born_lifecycle(self, lifecycle):
        assert _create(**EQUIPMENT, lifecycle=lifecycle)[1] == []

    def test_born_scrapped_is_400(self):
        _, errors = _create(**EQUIPMENT, lifecycle="scrapped")
        assert _fields(errors) == ["lifecycle"]

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


class TestModelAndRefusedFields:
    """S012 § 5.3 rules 1 and 6, § 5.4."""

    def test_a_model_is_required_on_create_with_its_own_message(self):
        body = {key: value for key, value in EQUIPMENT.items() if key != "model_id"}
        for data in (body, {**body, "model_id": None}):
            _, errors = _create(**data)
            assert errors == [{"field": "model_id", "message": PICK_A_MODEL}]
        assert PICK_A_MODEL == "Pick a model"

    def test_a_model_may_be_left_out_on_update_but_not_cleared(self):
        assert _update(name="x") == ({"name": "x"}, [])
        assert _update(model_id=9) == ({"model_id": 9}, [])
        assert _update(model_id=None)[1] == [{"field": "model_id", "message": PICK_A_MODEL}]
        # S033: a component unit may clear it, with its class
        assert _update(stored_level="component_unit", model_id=None, class_id=1) == (
            {"model_id": None, "class_id": 1}, [])

    @pytest.mark.parametrize("field, message", [
        ("make", "Make and model are now picked from Models"),
        ("model", "Make and model are now picked from Models"),
        ("class_id", "Class comes from the model"),   # S033: only beside a model
        ("type_id", "Type comes from the model"),
        ("status", "This field is now called Lifecycle. Reload the page."),   # S030 § 4.4
    ])
    @pytest.mark.parametrize("value", [None, 2, "Kirloskar"])
    def test_old_fields_are_refused_even_as_null(self, field, message, value):
        expected = [{"field": field, "message": message}]
        assert _create(**EQUIPMENT, **{field: value})[1] == expected
        assert _update(**{field: value})[1] == expected

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

    def test_scrapped_is_a_valid_target_lifecycle_on_update(self):
        assert _update(lifecycle="scrapped") == ({"lifecycle": "scrapped"}, [])


class TestNoModel:
    """S033 § 5.1: a component unit may have no model; its class and type are then picked."""

    UNIT = {"level": "component_unit", "parent_id": 5, "name": "Gearbox"}

    @staticmethod
    def _no_model(**data):
        """An update of a component unit without a model, of class 1 and (by default) no type."""
        return _update(stored_level="component_unit", stored_model_id=None, **data)

    def test_messages(self):
        assert (PICK_A_CLASS, PICK_A_TYPE, PICK_A_TYPE_OF_CLASS, CLASS_FROM_MODEL, TYPE_FROM_MODEL, NO_MODEL) == (
            "Pick a class", "Pick a type", "Pick a type of the new class, or No type",
            "Class comes from the model", "Type comes from the model", "No model")

    # --- the model ---

    @pytest.mark.parametrize("level, place", [
        ("equipment", {"unit_id": 1}), ("component_unit", {"parent_id": 5}), ("component", {"parent_id": 5}),
    ])
    def test_create_with_model_absent_is_pick_a_model_at_every_level(self, level, place):
        _, errors = _create(level=level, **place, name="x")
        assert errors == [{"field": "model_id", "message": PICK_A_MODEL}]

    def test_create_with_model_absent_and_class_and_type_sent_is_pick_a_model_only(self):   # BR3-01
        _, errors = _create(**self.UNIT, class_id=1, type_id=3)
        assert errors == [{"field": "model_id", "message": PICK_A_MODEL}]

    @pytest.mark.parametrize("level, place", [("equipment", {"unit_id": 1}), ("component", {"parent_id": 5})])
    def test_a_null_model_on_equipment_or_a_component_is_pick_a_model(self, level, place):
        _, errors = _create(level=level, **place, name="x", model_id=None, class_id=1)
        assert errors == [{"field": "model_id", "message": PICK_A_MODEL}]
        _, errors = _update(stored_level=level, model_id=None, class_id=1)
        assert errors == [{"field": "model_id", "message": PICK_A_MODEL}]

    def test_create_a_component_unit_without_a_model(self):
        clean, errors = _create(**self.UNIT, model_id=None, class_id=4, type_id=7)
        assert errors == []
        assert clean == {**self.UNIT, "model_id": None, "class_id": 4, "type_id": 7}

    def test_create_without_a_type_is_no_type(self):
        clean, errors = _create(**self.UNIT, model_id=None, class_id=4)
        assert errors == [] and clean["type_id"] is None
        clean, errors = _create(**self.UNIT, model_id=None, class_id=4, type_id=None)
        assert errors == [] and clean["type_id"] is None

    # --- class and type beside a model ---

    @pytest.mark.parametrize("value", [None, 1, 9])
    def test_class_or_type_beside_a_sent_model_is_refused(self, value):
        for field, message in (("class_id", CLASS_FROM_MODEL), ("type_id", TYPE_FROM_MODEL)):
            expected = [{"field": field, "message": message}]
            assert _create(**self.UNIT, model_id=2, **{field: value})[1] == expected
            assert self._no_model(model_id=2, **{field: value})[1] == expected

    def test_class_beside_a_stored_model_is_refused(self):
        assert _update(stored_level="component_unit", class_id=1)[1] == [
            {"field": "class_id", "message": CLASS_FROM_MODEL}]

    # --- class and type without a model ---

    @pytest.mark.parametrize("class_body", [{}, {"class_id": None}])
    def test_no_class_on_create_or_when_clearing_a_model_is_pick_a_class(self, class_body):
        expected = [{"field": "class_id", "message": PICK_A_CLASS}]
        assert _create(**self.UNIT, model_id=None, **class_body)[1] == expected
        assert _update(stored_level="component_unit", model_id=None, **class_body)[1] == expected

    def test_an_absent_class_on_a_no_model_node_keeps_the_stored_class(self):
        assert self._no_model(name="x") == ({"name": "x"}, [])
        assert self._no_model(model_id=None, name="x") == ({"model_id": None, "name": "x"}, [])

    def test_a_null_class_on_a_no_model_node_is_pick_a_class(self):
        assert self._no_model(class_id=None)[1] == [{"field": "class_id", "message": PICK_A_CLASS}]

    @pytest.mark.parametrize("raw", ["", "x", True, -1, 0, 1.5])
    def test_a_class_that_is_not_an_id_is_pick_a_class(self, raw):   # BR2-02
        expected = [{"field": "class_id", "message": PICK_A_CLASS}]
        assert self._no_model(class_id=raw)[1] == expected
        assert _create(**self.UNIT, model_id=None, class_id=raw)[1] == expected

    @pytest.mark.parametrize("raw", ["x", "", True, 0])
    def test_a_type_that_is_not_an_id_is_pick_a_type(self, raw):   # BR2-02
        assert self._no_model(type_id=raw)[1] == [{"field": "type_id", "message": PICK_A_TYPE}]

    def test_a_class_change_without_a_type_is_refused(self):   # BR1-01
        assert self._no_model(class_id=2)[1] == [{"field": "type_id", "message": PICK_A_TYPE_OF_CLASS}]

    def test_clearing_the_model_with_a_new_class_and_no_type_is_refused(self):   # BR1-01
        _, errors = _update(stored_level="component_unit", model_id=None, class_id=2)
        assert errors == [{"field": "type_id", "message": PICK_A_TYPE_OF_CLASS}]

    def test_clearing_the_model_with_the_same_class_keeps_the_type(self):
        clean, errors = _update(stored_level="component_unit", stored_type_id=3, model_id=None, class_id=1)
        assert errors == [] and clean == {"model_id": None, "class_id": 1}

    def test_a_class_change_with_a_type_or_no_type_is_accepted(self):
        assert self._no_model(class_id=2, type_id=8) == ({"class_id": 2, "type_id": 8}, [])
        assert self._no_model(class_id=2, type_id=None) == ({"class_id": 2, "type_id": None}, [])

    def test_a_type_alone_is_accepted(self):   # its class is the database's check (BR2-07)
        assert self._no_model(type_id=8) == ({"type_id": 8}, [])
        assert self._no_model(type_id=None) == ({"type_id": None}, [])

    def test_a_class_change_restating_the_stored_type_is_another_class(self):   # BR2-01
        expected = [{"field": "type_id", "message": "This type belongs to another class"}]
        assert self._no_model(stored_type_id=11, class_id=2, type_id=11)[1] == expected
        _, errors = _update(stored_level="component_unit", stored_type_id=11, model_id=None, class_id=2, type_id=11)
        assert errors == expected

    def test_a_class_change_with_no_type_on_a_node_without_one_is_accepted(self):   # BR3-02
        assert self._no_model(stored_type_id=None, class_id=2, type_id=None) == (
            {"class_id": 2, "type_id": None}, [])

    def test_an_unchanged_class_and_type_restated_are_accepted(self):
        assert self._no_model(stored_type_id=11, class_id=1, type_id=11) == ({"class_id": 1, "type_id": 11}, [])

    def test_update_without_a_model_on_a_no_model_node_with_class_and_type(self):
        assert self._no_model(class_id=2, type_id=5, name="Gearbox 2") == (
            {"class_id": 2, "type_id": 5, "name": "Gearbox 2"}, [])

    def test_setting_a_model_on_a_no_model_node(self):
        assert self._no_model(model_id=9) == ({"model_id": 9}, [])

    # --- history ---

    def test_tracked_changes_model_cleared_and_set_again(self):   # BR1-05
        with_model, without = _state(model_label="Atlas Copco GA37"), _state(model_label=None)
        assert tracked_changes(with_model, without) == [("model", "Atlas Copco GA37", NO_MODEL)]
        assert tracked_changes(without, with_model) == [("model", NO_MODEL, "Atlas Copco GA37")]
