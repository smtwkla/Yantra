"""PM plans — the pure rules of a machine's plan row (S104 § 5.5, § 8.2; no DB).  Since S104 a plan row holds only
the assignee and *Last done*; the work is its template's (test_pm_templates_core.py)."""

from datetime import date
from decimal import Decimal

import pytest

from meters_core import BELOW_ZERO, COUNTER
from pm_plans_core import (
    CHANGE_ON_TEMPLATE, EQUIPMENT_NEEDED, LAST_DONE_DATE, NO_METER_TRIGGER, OPERATOR_NO_ASSIGNEE, PLAN_FIXED,
    TEMPLATE_NEEDED, no_meter_here, plan_changes, plan_settings_error, schedule_changed, unknown_field,
    validate_attach, validate_plan_settings,
)

TODAY = date(2026, 11, 1)
HOURS = {"id": 5, "name": "Run hours", "unit": "h", "kind": "counter", "decimals": 1}
MAINTENANCE_METER = {"performer": "maintenance", "trigger_kind": "both"}


def _errors(body):
    return [(e["field"], e["message"]) for e in validate_plan_settings(body, False)[1]]


def _rules(clean, template=None, meter_type=HOURS, found=True):
    return plan_settings_error(clean, template or MAINTENANCE_METER, meter_type, found, TODAY)


class TestValidatePlanSettings:

    def test_any_subset_of_the_three_fields(self):
        assert validate_plan_settings({}, False) == ({}, [])
        clean, errors = validate_plan_settings({"assignee_id": 3, "last_done_on": "2026-10-02",
                                                "last_done_meter": "1840.5"}, False)
        assert errors == []
        assert clean == {"assignee_id": 3, "last_done_on": date(2026, 10, 2), "last_done_meter": Decimal("1840.5")}

    def test_null_clears(self):
        assert validate_plan_settings({"assignee_id": None, "last_done_on": None, "last_done_meter": None},
                                      False)[0] == {"assignee_id": None, "last_done_on": None, "last_done_meter": None}

    @pytest.mark.parametrize("raw", ["1999-12-31", "02-10-2026", "2026-13-01", 20261001])
    def test_a_bad_last_done_on(self, raw):
        assert _errors({"last_done_on": raw}) == [("last_done_on", LAST_DONE_DATE)]

    def test_a_bad_assignee_and_a_negative_seed(self):
        assert _errors({"assignee_id": "3"}) == [("assignee_id", "Choose a person from the list.")]
        assert _errors({"last_done_meter": "-1"}) == [("last_done_meter", BELOW_ZERO[COUNTER])]

    @pytest.mark.parametrize("field", ["items", "title", "name", "performer", "needs_verification", "trigger_kind",
                                       "calendar_every", "meter_type_id", "meter_every"])
    def test_the_work_is_changed_on_the_template(self, field):
        assert _errors({"assignee_id": None, field: 1}) == [(field, CHANGE_ON_TEMPLATE)]

    @pytest.mark.parametrize("field", ["template_id", "equipment_id"])
    def test_a_plan_stays_on_its_machine_and_template(self, field):
        assert _errors({field: 1}) == [(field, PLAN_FIXED)]

    def test_any_other_field_is_unknown(self):
        assert _errors({"active": False}) == [("active", "Unknown field: active.")]
        assert unknown_field("colour") == "Unknown field: colour."


class TestValidateAttach:

    def test_both_ids(self):
        assert validate_attach({"equipment_id": 4, "template_id": 9, "x": 1}, True) == (
            {"equipment_id": 4, "template_id": 9}, [])

    @pytest.mark.parametrize("body, field, message", [
        ({"template_id": 9}, "equipment_id", EQUIPMENT_NEEDED), ({"equipment_id": True, "template_id": 9},
                                                                  "equipment_id", EQUIPMENT_NEEDED),
        ({"equipment_id": 4}, "template_id", TEMPLATE_NEEDED), ({"equipment_id": 4, "template_id": "9"},
                                                                 "template_id", TEMPLATE_NEEDED),
    ])
    def test_a_missing_or_bad_id(self, body, field, message):
        assert [(e["field"], e["message"]) for e in validate_attach(body, True)[1]] == [(field, message)]


class TestPlanSettingsError:

    def test_good_settings(self):
        assert _rules({"assignee_id": 3, "last_done_on": TODAY, "last_done_meter": Decimal("1840.5")}) is None

    def test_last_done_on_up_to_today(self):
        assert _rules({"last_done_on": date(2026, 11, 2)}) == ("last_done_on", LAST_DONE_DATE)

    def test_an_operator_template_has_no_assignee(self):
        operator = {"performer": "operator", "trigger_kind": "calendar"}
        assert _rules({"assignee_id": 3}, operator, None) == ("assignee_id", OPERATOR_NO_ASSIGNEE)
        assert _rules({"assignee_id": None}, operator, None) is None

    def test_the_seed_needs_a_meter_trigger(self):
        calendar = {"performer": "maintenance", "trigger_kind": "calendar"}
        assert _rules({"last_done_meter": Decimal(10)}, calendar, None) == ("last_done_meter", NO_METER_TRIGGER)
        assert _rules({"last_done_meter": None}, calendar, None) is None

    def test_the_seed_needs_the_meter_on_this_machine(self):
        assert _rules({"last_done_meter": Decimal(10)}, found=False) == (
            "last_done_meter", "This machine has no Run hours meter. Add the meter first.")
        assert no_meter_here("Strokes") == "This machine has no Strokes meter. Add the meter first."

    def test_the_seed_takes_the_type_decimals(self):
        assert _rules({"last_done_meter": Decimal("0.05")}) == (
            "last_done_meter", "Enter a number with up to 1 decimal")

    def test_only_the_sent_fields_are_judged(self):
        operator = {"performer": "operator", "trigger_kind": "calendar"}
        assert _rules({"last_done_on": TODAY}, operator, None) is None


def test_plan_changes():
    stored = {"assignee_id": 3, "last_done_on": date(2026, 10, 2), "last_done_meter": Decimal("250.000")}
    assert plan_changes(stored, {"assignee_id": 3, "last_done_on": date(2026, 10, 3),
                                 "last_done_meter": Decimal("250")}) == {"last_done_on": date(2026, 10, 3)}


class TestPlanChangesTiesTheSeedToTheMeter:
    """CR1-05: the same *Last done* meter value, sent again, is a change when the stored seed was entered for
    another meter than the plan uses now."""

    PRESS_HOURS, PART_HOURS = (4, 7), (5, 7)

    def _stored(self, seed_meter):
        return {"assignee_id": None, "last_done_on": None, "last_done_meter": Decimal("1840.000"),
                "seed_meter_equipment_id": seed_meter and seed_meter[0],
                "seed_meter_type_id": seed_meter and seed_meter[1]}

    def test_the_same_value_for_another_meter_is_a_change(self):
        stored = self._stored(self.PRESS_HOURS)
        assert plan_changes(stored, {"last_done_meter": Decimal("1840")}, self.PART_HOURS) == {
            "last_done_meter": Decimal("1840")}

    def test_the_same_value_for_the_same_meter_is_no_change(self):
        stored = self._stored(self.PART_HOURS)
        assert plan_changes(stored, {"last_done_meter": Decimal("1840")}, self.PART_HOURS) == {}

    def test_without_a_meter_now_or_without_a_value_nothing_is_tied(self):
        stored = self._stored(self.PRESS_HOURS)
        assert plan_changes(stored, {"last_done_meter": Decimal("1840")}, None) == {}
        assert plan_changes(stored, {"last_done_meter": Decimal("1840")}) == {}
        assert plan_changes(stored, {"assignee_id": None}, self.PART_HOURS) == {}
        assert plan_changes(stored, {"last_done_meter": None}, self.PART_HOURS) == {"last_done_meter": None}

    def test_a_different_value_is_a_change_as_before(self):
        stored = self._stored(self.PART_HOURS)
        assert plan_changes(stored, {"last_done_meter": Decimal("1900")}, self.PART_HOURS) == {
            "last_done_meter": Decimal("1900")}


class TestScheduleChanged:
    """CR4-01: a change drops the open job's reschedule (S101 D4) only when it can move the base of the next due.
    Clearing a seed the plan does not use (entered for another meter than the trigger now resolves to) cannot."""

    PRESS_HOURS, PART_HOURS = (4, 7), (5, 7)
    CLEAR = {"last_done_meter": None}

    def _stored(self, seed_meter):
        return {"last_done_on": None, "last_done_meter": Decimal("1840.000"),
                "seed_meter_equipment_id": seed_meter and seed_meter[0],
                "seed_meter_type_id": seed_meter and seed_meter[1]}

    def test_clearing_an_unused_seed_is_no_schedule_change(self):
        assert schedule_changed(self._stored(self.PRESS_HOURS), self.CLEAR, self.PART_HOURS) is False

    def test_clearing_a_seed_when_no_meter_resolves_is_no_schedule_change(self):
        assert schedule_changed(self._stored(self.PRESS_HOURS), self.CLEAR, None) is False

    def test_clearing_the_seed_the_plan_uses_is_a_schedule_change(self):
        assert schedule_changed(self._stored(self.PART_HOURS), self.CLEAR, self.PART_HOURS) is True

    def test_a_new_value_or_a_new_date_is_a_schedule_change_as_before(self):
        stored = self._stored(self.PRESS_HOURS)
        assert schedule_changed(stored, {"last_done_meter": Decimal("1900")}, self.PART_HOURS) is True
        assert schedule_changed(stored, {"last_done_on": date(2026, 10, 3)}, self.PART_HOURS) is True
        assert schedule_changed(stored, {"last_done_on": date(2026, 10, 3), "last_done_meter": None},
                                self.PART_HOURS) is True

    def test_an_assignee_change_or_no_change_is_none(self):
        stored = self._stored(self.PART_HOURS)
        assert schedule_changed(stored, {"assignee_id": 3}, self.PART_HOURS) is False
        assert schedule_changed(stored, {}, self.PART_HOURS) is False
