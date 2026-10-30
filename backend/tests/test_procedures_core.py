"""One-point lessons — pure rules (S075 § 8.2; no DB)."""

import pytest

import improvements_core
from procedures_core import (
    ACTION_NEEDED, ACTIVE_NOT_BOOL, BODY_MAX, BODY_NEEDED, BODY_NOT_TEXT, BODY_TOO_LONG, FOR_CLASS_NOT_BOOL, LINK_KEPT,
    MACHINE_NEEDED, NOT_A_LESSON_ACTION, TITLE_MAX, TITLE_NEEDED, TITLE_NOT_TEXT, TITLE_TOO_LONG, already_has_lesson,
    format_lesson_serial, lesson_flags, lesson_link_error, lesson_machine_message, link_kept_error, may_write_lesson,
    validate_lesson,
)

GOOD = {"equipment_id": 7, "title": "Keep the panel door shut", "body": "Dust trips the contactor."}
# A Tamil letter with a vowel sign is two code points: "கொ" is க + ொ
TAMIL_80 = "கொ" * 40
TAMIL_81 = TAMIL_80 + "க"


def _errors(body, creating=True):
    return [(e["field"], e["message"]) for e in validate_lesson(body, creating)[1]]


class TestValidateCreate:

    def test_a_good_create_takes_the_defaults(self):
        assert validate_lesson(GOOD, True) == ({**GOOD, "for_class": False, "action_id": None}, [])

    def test_the_class_tick_and_a_countermeasure(self):
        clean, errors = validate_lesson({**GOOD, "for_class": True, "action_id": 12}, True)
        assert errors == [] and (clean["for_class"], clean["action_id"]) == (True, 12)

    @pytest.mark.parametrize("field, message", [
        ("equipment_id", MACHINE_NEEDED), ("title", TITLE_NEEDED), ("body", BODY_NEEDED)])
    def test_each_required_field(self, field, message):
        body = {k: v for k, v in GOOD.items() if k != field}
        assert _errors(body) == [(field, message)]

    @pytest.mark.parametrize("value", [True, False, 0, -1, "7", 7.0, None])
    def test_equipment_id_must_be_an_id_not_a_boolean(self, value):
        assert _errors({**GOOD, "equipment_id": value}) == [("equipment_id", MACHINE_NEEDED)]

    @pytest.mark.parametrize("field, needed", [("title", TITLE_NEEDED), ("body", BODY_NEEDED)])
    def test_empty_after_trim(self, field, needed):
        assert _errors({**GOOD, field: " \n\t "}) == [(field, needed)]

    @pytest.mark.parametrize("field, maximum, too_long", [
        ("title", TITLE_MAX, TITLE_TOO_LONG), ("body", BODY_MAX, BODY_TOO_LONG)])
    def test_the_bounds(self, field, maximum, too_long):
        assert _errors({**GOOD, field: "x" * maximum}) == []
        assert _errors({**GOOD, field: "x" * (maximum + 1)}) == [(field, too_long)]

    @pytest.mark.parametrize("field, not_text", [("title", TITLE_NOT_TEXT), ("body", BODY_NOT_TEXT)])
    def test_a_number_is_not_text(self, field, not_text):
        assert _errors({**GOOD, field: 5}) == [(field, not_text)]

    def test_the_title_collapses_whitespace_and_the_body_keeps_its_line_breaks(self):
        clean, errors = validate_lesson({**GOOD, "title": "  Keep  the\npanel ", "body": " Line one\nவரி இரண்டு \n"},
                                        True)
        assert errors == []
        assert clean["title"] == "Keep the panel"
        assert clean["body"] == "Line one\nவரி இரண்டு"

    def test_the_title_is_bounded_after_collapsing(self):
        assert _errors({**GOOD, "title": "x" * 40 + "      " + "y" * 39}) == []

    def test_a_tamil_title_of_80_characters_passes_and_81_is_refused(self):
        assert len(TAMIL_80) == TITLE_MAX
        assert validate_lesson({**GOOD, "title": TAMIL_80}, True)[0]["title"] == TAMIL_80
        assert _errors({**GOOD, "title": TAMIL_81}) == [("title", TITLE_TOO_LONG)]

    @pytest.mark.parametrize("value", ["yes", 1, None])
    def test_for_class_must_be_a_boolean(self, value):
        assert _errors({**GOOD, "for_class": value}) == [("for_class", FOR_CLASS_NOT_BOOL)]

    @pytest.mark.parametrize("value", [0, True, "3"])
    def test_action_id_must_be_an_id_or_null(self, value):
        assert _errors({**GOOD, "action_id": value}) == [("action_id", ACTION_NEEDED)]

    def test_active_and_kind_on_a_create_are_ignored(self):
        clean, errors = validate_lesson({**GOOD, "active": False, "kind": "work_instruction", "x": 1}, True)
        assert errors == [] and {"active", "kind", "x"}.isdisjoint(clean)


class TestValidateChange:

    def test_an_empty_change_is_no_change(self):
        assert validate_lesson({}, False) == ({}, [])

    def test_equipment_id_is_ignored(self):
        assert validate_lesson({"equipment_id": "x"}, False) == ({}, [])

    def test_each_field(self):
        clean, errors = validate_lesson({"title": "New", "body": "Text", "for_class": True, "action_id": None,
                                         "active": False}, False)
        assert errors == []
        assert clean == {"title": "New", "body": "Text", "for_class": True, "action_id": None, "active": False}

    @pytest.mark.parametrize("field, needed", [("title", TITLE_NEEDED), ("body", BODY_NEEDED)])
    def test_null_is_refused(self, field, needed):
        assert _errors({field: None}, False) == [(field, needed)]

    @pytest.mark.parametrize("value", ["no", 0, None])
    def test_active_must_be_a_boolean(self, value):
        assert _errors({"active": value}, False) == [("active", ACTIVE_NOT_BOOL)]


def test_format_lesson_serial():
    assert [format_lesson_serial(n) for n in (1, 7, 999, 1000)] == ["OPL-001", "OPL-007", "OPL-999", "OPL-1000"]


def test_the_messages_name_the_machine_and_the_lesson():
    assert lesson_machine_message("HP003") == (
        "A lesson for this countermeasure goes on HP003, the improvement's machine")
    assert already_has_lesson("OPL-007") == "This countermeasure already has its lesson, OPL-007"


class TestLink:

    @pytest.mark.parametrize("state", ["open", "done"])
    def test_a_lesson_countermeasure_open_or_done_links(self, state):
        assert lesson_link_error("lesson", state) is None

    def test_another_kind_is_refused(self):
        assert lesson_link_error("corrective", "open") == NOT_A_LESSON_ACTION

    def test_a_cancelled_one_is_refused_with_s070s_words(self):
        assert lesson_link_error("lesson", "cancelled") == improvements_core.WAS_CANCELLED

    def test_the_link_is_set_once(self):
        assert link_kept_error(None, 5) is None
        assert link_kept_error(None, None) is None
        assert link_kept_error(5, 5) is None
        assert link_kept_error(5, 6) == LINK_KEPT
        assert link_kept_error(5, None) == LINK_KEPT


class TestFlags:

    @pytest.mark.parametrize("for_class, edit_here, edit_anywhere, can_edit, can_change_class", [
        (False, True, True, True, True),
        (False, False, True, False, False),
        (False, False, False, False, False),
        (True, True, True, True, True),
        (True, False, True, True, False),
        (True, False, False, False, False),
    ])
    def test_lesson_flags(self, for_class, edit_here, edit_anywhere, can_edit, can_change_class):
        assert lesson_flags(for_class, edit_here, edit_anywhere) == {
            "can_edit": can_edit, "can_change_class": can_change_class}

    @pytest.mark.parametrize("kind, state, has_lesson, may_create, expected", [
        ("lesson", "open", False, True, True),
        ("lesson", "done", False, True, True),
        ("lesson", "open", True, True, False),
        ("lesson", "cancelled", False, True, False),
        ("corrective", "open", False, True, False),
        ("lesson", "open", False, False, False),
    ])
    def test_may_write_lesson(self, kind, state, has_lesson, may_create, expected):
        assert may_write_lesson(kind, state, has_lesson, may_create) is expected
