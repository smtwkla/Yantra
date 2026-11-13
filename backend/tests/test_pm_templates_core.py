"""PM templates — the pure rules (S104 § 5.1, § 5.2, § 8.2; no DB).  S096's trigger and item rules, moved from
test_pm_plans_core.py with the template's changes: the trigger names a meter type, and the two reading kinds.  A1:
the parent tick is gone; a body that still sends ``meter_from_parent`` has it ignored."""

from decimal import Decimal

import pytest

from meters_core import MIN_ABOVE_MAX
from pm_templates_core import (
    ABOVE_ZERO, BEFORE_USE_NOT_YET, CLEAR_CALENDAR, CLEAR_METER, COUNTER_NEEDED, ITEM_METER_TYPE_NEEDED,
    ITEM_TEXT_NEEDED, ITEM_TYPE_NEEDED, ITEMS_NEEDED, ITEMS_NOT_LIST, MAX_ITEMS, METER_LIMITS, METER_TYPE_FROM_LIST,
    METER_UNIT, NAME_NEEDED, ONLY_METER_READING, ONLY_READING, PERFORMER_NEEDED, PHOTO_NEEDED, READING_KIND_NEEDED,
    TOO_MANY_ITEMS, TRIGGER_NEEDED, UNIT_NEEDED, calendar_message, default_verification,
    interval_number, item_limits_text, meter_label, sent_meter_type_ids, sync_items, template_changes,
    template_rules_error, trigger_text, validate_item, validate_items, validate_template,
)

HOURS = {"id": 5, "name": "Run hours", "unit": "h", "kind": "counter", "decimals": 1}
STROKES = {"id": 6, "name": "Strokes", "unit": "strokes", "kind": "counter", "decimals": 0}
OIL = {"id": 7, "name": "Oil temperature", "unit": "°C", "kind": "gauge", "decimals": 1}
OUTPUT = {"id": 8, "name": "Output", "unit": "pcs", "kind": "amount", "decimals": 0}
TYPES = {t["id"]: t for t in (HOURS, STROKES, OIL, OUTPUT)}
ITEM = {"item_type": "check", "text": "No oil leaks at the cylinder seals"}
GOOD = {"name": "Press — monthly hydraulic check", "trigger_kind": "calendar", "calendar_every": 1,
        "calendar_unit": "month", "items": [ITEM]}
EMPTY = {"trigger_kind": "calendar", "calendar_every": 1, "calendar_unit": "month", "meter_type_id": None,
         "meter_every": None}
MEASURE = {"item_type": "reading", "reading_kind": "measurement", "text": "Main pressure"}
METER_ITEM = {"item_type": "reading", "reading_kind": "meter", "text": "Oil temperature", "meter_type_id": 7}


def _errors(body, creating=True):
    return [(e["field"], e["message"]) for e in validate_template(body, creating)[1]]


def _first(body, creating=True):
    return _errors(body, creating)[0]


def _rules(meter_type=None, **fields):
    return template_rules_error({**EMPTY, **fields}, meter_type)


def _item(body):
    clean, errors = validate_item(body, TYPES)
    return clean, [(e["field"], e["message"]) for e in errors]


class TestValidateTemplate:

    def test_a_good_create_takes_the_defaults(self):
        clean, errors = validate_template(GOOD, True)
        assert errors == []
        assert clean["performer"] == "maintenance" and clean["needs_verification"] == 1
        assert "meter_from_parent" not in clean
        assert clean["name"] == GOOD["name"] and clean["items"] == [ITEM]

    def test_an_operator_template_needs_no_verification_by_default(self):
        clean, _ = validate_template({**GOOD, "performer": "operator"}, True)
        assert clean["needs_verification"] == 0
        assert validate_template({**GOOD, "performer": "operator", "needs_verification": True}, True)[0][
            "needs_verification"] == 1

    def test_every_required_field_missing_on_a_create(self):
        assert _errors({}) == [("name", NAME_NEEDED), ("trigger_kind", TRIGGER_NEEDED), ("items", ITEMS_NEEDED)]

    def test_nothing_is_required_on_a_change(self):
        assert validate_template({}, False) == ({}, [])

    def test_the_name_is_collapsed_and_bounded(self):
        assert validate_template({"name": "  Monthly   check "}, False)[0]["name"] == "Monthly check"
        assert _errors({"name": "x" * 100}, False) == []
        assert _first({"name": "x" * 101}, False) == ("name", "Name must be at most 100 characters")
        assert _first({"name": "   "}, False) == ("name", NAME_NEEDED)

    def test_the_performer_is_checked_with_its_case(self):
        assert _first({"performer": "Operator"}, False) == ("performer", PERFORMER_NEEDED)

    def test_before_use_is_refused_for_now(self):
        assert _first({**GOOD, "trigger_kind": "before_use"}) == ("trigger_kind", BEFORE_USE_NOT_YET)

    @pytest.mark.parametrize("raw", [True, "3", 0, 1.5])
    def test_a_bad_calendar_every(self, raw):
        assert _first({**GOOD, "calendar_every": raw}) == ("calendar_every", calendar_message("month"))

    def test_a_bad_calendar_unit(self):
        assert _first({**GOOD, "calendar_unit": "months"}) == ("calendar_unit", UNIT_NEEDED)

    def test_the_meter_type(self):
        assert _first({"meter_type_id": "5"}, False) == ("meter_type_id", METER_TYPE_FROM_LIST)

    def test_the_old_parent_tick_is_ignored(self):
        # A1.3: a body that still sends the tick is not refused; the field is ignored as any unknown field
        assert validate_template({"meter_from_parent": True}, False) == ({}, [])
        assert validate_template({"meter_from_parent": "yes"}, False) == ({}, [])
        assert "meter_from_parent" not in validate_template({**GOOD, "meter_from_parent": True}, True)[0]

    def test_meter_every_is_a_decimal(self):
        assert validate_template({"meter_every": "250"}, False)[0] == {"meter_every": Decimal("250")}

    def test_active_is_ignored_on_a_create_and_a_flag_on_a_change(self):
        assert "active" not in validate_template({**GOOD, "active": False}, True)[0]
        assert validate_template({"active": False}, False)[0] == {"active": 0}

    def test_items_must_be_a_list(self):
        assert _first({**GOOD, "items": {"a": 1}}) == ("items", ITEMS_NOT_LIST)

    def test_the_old_plan_fields_are_ignored(self):
        assert validate_template({"assignee_id": 3, "meter_equipment_id": 4}, False) == ({}, [])


class TestTemplateRules:

    def test_a_good_calendar_template(self):
        assert _rules() is None

    def test_a_good_both_template(self):
        assert _rules(HOURS, trigger_kind="both", meter_type_id=5, meter_every=Decimal("250")) is None

    def test_a_calendar_template_without_its_fields(self):
        assert _rules(calendar_every=None) == ("calendar_every", calendar_message("month"))
        assert _rules(calendar_unit=None) == ("calendar_unit", UNIT_NEEDED)

    def test_a_calendar_template_with_meter_fields(self):
        assert _rules(meter_type_id=5) == ("meter_type_id", CLEAR_METER)
        assert _rules(meter_every=Decimal("5")) == ("meter_every", CLEAR_METER)

    def test_a_meter_template_with_calendar_fields(self):
        assert _rules(HOURS, trigger_kind="meter", meter_type_id=5, meter_every=Decimal("250")) == (
            "calendar_every", CLEAR_CALENDAR)

    def test_a_meter_template_without_its_fields(self):
        meter = {"trigger_kind": "meter", "calendar_every": None, "calendar_unit": None}
        assert _rules(**meter, meter_every=Decimal("250")) == ("meter_type_id", METER_TYPE_FROM_LIST)
        assert _rules(HOURS, **meter, meter_type_id=5) == ("meter_every", ABOVE_ZERO)

    def test_the_trigger_needs_a_counter(self):
        meter = {"trigger_kind": "meter", "calendar_every": None, "calendar_unit": None, "meter_every": Decimal(5)}
        assert _rules(OIL, **meter, meter_type_id=7) == ("meter_type_id", COUNTER_NEEDED)
        assert _rules(OUTPUT, **meter, meter_type_id=8) == ("meter_type_id", COUNTER_NEEDED)

    @pytest.mark.parametrize("unit, most", [("day", 3650), ("week", 520), ("month", 120), ("year", 10)])
    def test_the_unit_maximum(self, unit, most):
        assert _rules(calendar_unit=unit, calendar_every=most) is None
        assert _rules(calendar_unit=unit, calendar_every=most + 1) == ("calendar_every", calendar_message(unit))

    @pytest.mark.parametrize("every, message", [("0.05", "Enter a number with up to 1 decimal"),
                                                ("0", ABOVE_ZERO), ("-5", ABOVE_ZERO)])
    def test_a_bad_meter_every_on_a_one_decimal_type(self, every, message):
        assert _rules(HOURS, trigger_kind="both", meter_type_id=5, meter_every=Decimal(every)) == (
            "meter_every", message)


class TestSmallRules:

    def test_default_verification(self):
        assert default_verification("maintenance") is True
        assert default_verification("operator") is False

    @pytest.mark.parametrize("value, decimals, text", [
        ("250", 1, "250"), ("250.0", 1, "250"), ("0.5", 1, "0.5"), ("5000", 0, "5,000"),
        ("1234567.8", 1, "12,34,567.8"), ("62.50", 3, "62.5"), ("-20", 1, "-20"),
    ])
    def test_interval_number(self, value, decimals, text):
        assert interval_number(Decimal(value), decimals) == text

    def test_meter_label(self):
        assert meter_label("HP003", HOURS) == "HP003's Run hours"

    def test_the_meter_types_a_body_names(self):
        body = {"meter_type_id": 5, "items": [ITEM, METER_ITEM, {**METER_ITEM, "meter_type_id": True}, "x"]}
        assert sent_meter_type_ids(body) == [5, 7]

    def test_template_changes(self):
        stored = {"name": "Check", "needs_verification": 1, "meter_every": Decimal("250.000"), "active": 1}
        assert template_changes(stored, {"name": "Check", "needs_verification": 0, "meter_every": Decimal("250"),
                                         "active": 1, "items": []}) == {"needs_verification": 0}


class TestTriggerText:

    @pytest.mark.parametrize("every, unit, text", [
        (1, "day", "Every day"), (3, "day", "Every 3 days"), (1, "week", "Every week"), (2, "week", "Every 2 weeks"),
        (1, "month", "Every month"), (6, "month", "Every 6 months"), (1, "year", "Every year"),
        (2, "year", "Every 2 years"),
    ])
    def test_calendar(self, every, unit, text):
        assert trigger_text({"trigger_kind": "calendar", "calendar_every": every, "calendar_unit": unit}, None) == text

    @pytest.mark.parametrize("every, meter_type, text", [
        ("250.000", HOURS, "Every 250 h"), ("5000", HOURS, "Every 5,000 h"), ("0.5", HOURS, "Every 0.5 h"),
        ("10000", STROKES, "Every 10,000 strokes"),
    ])
    def test_meter(self, every, meter_type, text):
        assert trigger_text({"trigger_kind": "meter", "meter_every": Decimal(every)}, meter_type) == text

    def test_both(self):
        template = {"trigger_kind": "both", "calendar_every": 1, "calendar_unit": "month",
                    "meter_every": Decimal("250")}
        assert trigger_text(template, HOURS) == "Every month or 250 h, whichever comes first"

    def test_before_use(self):
        assert trigger_text({"trigger_kind": "before_use"}, None) == "Before each use"


class TestValidateItem:

    def test_a_check_takes_the_defaults(self):
        clean, errors = _item(ITEM)
        assert errors == []
        assert clean == {"id": None, "item_type": "check", "text": ITEM["text"], "help_text": None,
                         "photo": "optional", "reading_kind": None, "unit": None, "min_value": None,
                         "max_value": None, "meter_type_id": None}

    def test_an_existing_item_keeps_its_id(self):
        assert _item({**ITEM, "id": 4})[0]["id"] == 4
        assert _item({**ITEM, "id": "4"})[1] == [("id", "Reload the page.")]

    def test_the_required_fields(self):
        assert _item({})[1][:2] == [("item_type", ITEM_TYPE_NEEDED), ("text", ITEM_TEXT_NEEDED)]

    def test_the_text_and_the_help_text(self):
        assert _item({**ITEM, "text": "  Grease   the bearing "})[0]["text"] == "Grease the bearing"
        assert _item({**ITEM, "text": "x" * 201})[1] == [("text", "Item must be at most 200 characters")]
        assert _item({**ITEM, "help_text": " One\nTwo "})[0]["help_text"] == "One\nTwo"

    def test_the_photo_setting(self):
        assert _item({**ITEM, "photo": "always"})[1] == [("photo", PHOTO_NEEDED)]

    @pytest.mark.parametrize("field, value", [("reading_kind", "measurement"), ("unit", "mm"), ("min_value", "1"),
                                              ("max_value", "2"), ("meter_type_id", 7)])
    def test_only_a_reading_has_a_reading_field(self, field, value):
        assert _item({"item_type": "task", "text": "Grease", field: value})[1] == [(field, ONLY_READING)]

    def test_a_task_may_send_the_empty_reading_fields(self):
        assert _item({"item_type": "task", "text": "Grease", "reading_kind": None, "unit": None,
                      "meter_type_id": None})[1] == []

    def test_the_old_parent_tick_is_ignored_on_any_item(self):
        assert _item({"item_type": "task", "text": "Grease", "meter_from_parent": True})[1] == []
        clean, errors = _item({**METER_ITEM, "meter_from_parent": True})
        assert errors == [] and "meter_from_parent" not in clean

    def test_a_reading_needs_its_kind(self):
        assert _item({"item_type": "reading", "text": "Gap"})[1] == [("reading_kind", READING_KIND_NEEDED)]
        assert _item({"item_type": "reading", "text": "Gap", "reading_kind": "value"})[1] == [
            ("reading_kind", READING_KIND_NEEDED)]


class TestMeasurement:

    def test_a_unit_and_limits(self):
        clean, errors = _item({**MEASURE, "unit": "bar", "min_value": "180", "max_value": "200"})
        assert errors == []
        assert (clean["reading_kind"], clean["unit"], clean["min_value"], clean["max_value"]) == (
            "measurement", "bar", Decimal("180"), Decimal("200"))

    def test_min_equal_to_max_passes_min_above_max_fails(self):
        assert _item({**MEASURE, "min_value": "5", "max_value": "5"})[1] == []
        assert _item({**MEASURE, "min_value": "6", "max_value": "5"})[1] == [("max_value", MIN_ABOVE_MAX)]

    def test_the_unit_is_bounded(self):
        assert _item({**MEASURE, "unit": "x" * 21})[1] == [("unit", "Unit must be at most 20 characters")]

    def test_no_meter_type(self):
        assert _item({**MEASURE, "meter_type_id": 7})[1] == [("meter_type_id", ONLY_METER_READING)]


class TestMeterReading:

    def test_a_gauge_type(self):
        clean, errors = _item(METER_ITEM)
        assert errors == []
        assert (clean["reading_kind"], clean["meter_type_id"]) == ("meter", 7)
        assert (clean["unit"], clean["min_value"], clean["max_value"]) == (None, None, None)

    def test_a_counter_type(self):
        clean, errors = _item({**METER_ITEM, "meter_type_id": 5})
        assert errors == [] and clean["meter_type_id"] == 5

    @pytest.mark.parametrize("meter_type_id", [None, 8, 99])
    def test_a_counter_or_gauge_type_is_needed(self, meter_type_id):
        assert _item({**METER_ITEM, "meter_type_id": meter_type_id})[1] == [
            ("meter_type_id", ITEM_METER_TYPE_NEEDED)]

    def test_no_unit(self):
        assert _item({**METER_ITEM, "unit": "°C"})[1] == [("unit", METER_UNIT)]

    @pytest.mark.parametrize("field", ["min_value", "max_value"])
    def test_no_limits_of_its_own(self, field):
        assert _item({**METER_ITEM, field: "60"})[1] == [(field, METER_LIMITS)]


class TestValidateItems:

    def test_not_a_list_and_empty(self):
        assert validate_items("x", TYPES) == ([], ("items", ITEMS_NOT_LIST))
        assert validate_items([], TYPES) == ([], ("items", ITEMS_NEEDED))

    def test_the_most_items(self):
        items, error = validate_items([ITEM] * MAX_ITEMS, TYPES)
        assert error is None and len(items) == MAX_ITEMS
        assert validate_items([ITEM] * (MAX_ITEMS + 1), TYPES) == ([], ("items", TOO_MANY_ITEMS))

    def test_the_item_number_leads_the_message(self):
        assert validate_items([ITEM, ITEM, {"item_type": "check"}], TYPES) == (
            [], ("items", "Item 3: " + ITEM_TEXT_NEEDED))
        assert validate_items([ITEM, "x"], TYPES) == ([], ("items", "Item 2: Reload the page."))


def _stored(item_id, position, text, **fields):
    return {"id": item_id, "position": position, "item_type": "check", "text": text, "help_text": None,
            "photo": "optional", "reading_kind": None, "unit": None, "min_value": None, "max_value": None,
            "meter_type_id": None, **fields}


def _sent(item_id, text, **fields):
    row = _stored(item_id, 0, text, **fields)
    del row["position"]
    return row


class TestSyncItems:

    STORED = [_stored(1, 1, "One"), _stored(2, 2, "Two"), _stored(3, 3, "Three")]

    def test_nothing_changed_writes_nothing(self):
        assert sync_items(self.STORED, [_sent(1, "One"), _sent(2, "Two"), _sent(3, "Three")]) == (
            {"insert": [], "update": [], "deactivate": []}, None)

    def test_an_update_writes_the_changed_fields_only(self):
        ops, error = sync_items(self.STORED, [_sent(1, "One"), _sent(2, "Two!", photo="required"), _sent(3, "Three")])
        assert error is None and ops["update"] == [(2, {"text": "Two!", "photo": "required"})]

    def test_a_change_of_kind_is_a_change_of_the_same_item(self):
        stored = [_stored(1, 1, "Oil", item_type="reading", reading_kind="measurement", unit="°C")]
        ops, _ = sync_items(stored, [_sent(1, "Oil", item_type="reading", reading_kind="meter", meter_type_id=7)])
        assert ops["update"] == [(1, {"reading_kind": "meter", "unit": None, "meter_type_id": 7})]
        assert ops["insert"] == [] and ops["deactivate"] == []

    def test_a_decimal_equal_by_value_is_no_change(self):
        stored = [_stored(1, 1, "Gap", item_type="reading", reading_kind="measurement", min_value=Decimal("30.000"))]
        assert sync_items(stored, [_sent(1, "Gap", item_type="reading", reading_kind="measurement",
                                         min_value=Decimal("30"))])[0]["update"] == []

    def test_a_move_a_removal_and_an_insert(self):
        ops, _ = sync_items(self.STORED, [_sent(3, "Three"), _sent(None, "New")])
        assert ops["update"] == [(3, {"position": 1})] and ops["insert"][0]["position"] == 2
        assert "id" not in ops["insert"][0]
        assert ops["deactivate"] == [1, 2]

    def test_an_unknown_id_and_an_id_twice(self):
        assert sync_items(self.STORED, [_sent(1, "One"), _sent(9, "Nine")]) == (
            None, "Item 2 was removed or changed by someone else. Reload the page.")
        assert sync_items(self.STORED, [_sent(1, "One"), _sent(1, "One")]) == (
            None, "Item 2 appears twice. Reload the page.")


class TestItemLimitsText:

    def test_a_task_or_check_has_none(self):
        assert item_limits_text({"item_type": "check"}) is None

    def test_a_measurement(self):
        item = {"item_type": "reading", "reading_kind": "measurement", "unit": "bar"}
        assert item_limits_text({**item, "min_value": Decimal("180"), "max_value": Decimal("200")}) == (
            "Measurement · 180–200 bar")
        assert item_limits_text({**item, "max_value": Decimal("60")}) == "Measurement · up to 60 bar"
        assert item_limits_text({**item, "unit": None, "min_value": Decimal("1.5"), "max_value": Decimal("2")}) == (
            "Measurement · 1.5–2")
        assert item_limits_text(item) == "Measurement"

    def test_a_meter_reading_on_a_template(self):
        item = {"item_type": "reading", "reading_kind": "meter"}
        assert item_limits_text(item, OIL) == "Meter reading · Oil temperature"

    def test_a_meter_reading_on_a_job_names_its_node_and_the_limits_in_force(self):
        item = {"item_type": "reading", "reading_kind": "meter", "min_value": Decimal("20.000"),
                "max_value": Decimal("70.000")}
        assert item_limits_text(item, OIL, "HP003") == "Meter reading · HP003's Oil temperature · 20–70 °C"
        assert item_limits_text({"item_type": "reading", "reading_kind": "meter"}, HOURS, "HP002") == (
            "Meter reading · HP002's Run hours")
