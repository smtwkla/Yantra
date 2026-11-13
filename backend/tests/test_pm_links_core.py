"""pm_links_core — which templates reach a node, the plan rows to make, relink or unlink, the meters a template
needs, whether it applies, and why a plan stops (docs/steps/S104-pm-templates-one-path/1-brief.md § 5.3, § 5.4,
§ 8.2).  Pure: no database.
"""

import pytest

from pm_jobs_core import TEMPLATE_INACTIVE_REMARK, UNLINKED_REMARK
from pm_links_core import (
    applies, missing_text, needed_meters, plan_actions, reaching_templates, resolve_meters, stop_remark,
)

HOURS, OIL, GAP = 11, 12, 13
NODE = {"id": 5, "class_id": 1, "type_id": 2, "model_id": 3}


def link(template_id, target_kind="equipment", target_id=5, active=1):
    return {"template_id": template_id, "target_kind": target_kind, "target_id": target_id, "active": active}


def item(meter_type_id, kind="meter"):
    return {"item_type": "reading", "reading_kind": kind, "meter_type_id": meter_type_id}


def template(trigger_kind="meter", meter_type_id=HOURS):
    return {"trigger_kind": trigger_kind, "meter_type_id": meter_type_id}


class TestReachingTemplates:

    def test_only_the_active_equipment_links_naming_the_node(self):
        links = [link(1), link(2, active=0), link(3, target_id=6), link(4, "model", 3), link(1), link(9)]
        assert reaching_templates(NODE, links) == [1, 9]

    def test_no_links(self):
        assert reaching_templates(NODE, []) == []


class TestPlanActions:

    def test_make_relink_unlink_and_nothing(self):
        plans = [{"id": 70, "template_id": 1, "linked": 1},     # reached, linked: nothing
                 {"id": 71, "template_id": 2, "linked": 0},     # reached again: relink
                 {"id": 72, "template_id": 3, "linked": 1},     # no longer reached: unlink
                 {"id": 73, "template_id": 4, "linked": 0}]     # not reached, unlinked: nothing
        assert plan_actions([1, 2, 5], plans) == {"make": [5], "relink": [71], "unlink": [72]}

    def test_a_row_linked_and_reached_needs_nothing(self):
        assert plan_actions([1], [{"id": 70, "template_id": 1, "linked": 1}]) == {
            "make": [], "relink": [], "unlink": []}

    def test_an_empty_node(self):
        assert plan_actions([], []) == {"make": [], "relink": [], "unlink": []}

    def test_every_reaching_template_without_a_row_is_made_once(self):
        assert plan_actions([3, 1, 3], []) == {"make": [1, 3], "relink": [], "unlink": []}


class TestNeededMeters:

    def test_the_trigger_only(self):
        assert needed_meters(template(), []) == [HOURS]

    def test_a_calendar_trigger_needs_nothing(self):
        assert needed_meters(template("calendar", None), []) == []

    def test_the_items_only(self):
        items = [item(OIL), {"item_type": "check", "reading_kind": None, "meter_type_id": None},
                 item(None, kind="measurement"), item(GAP)]
        assert needed_meters(template("calendar", None), items) == [OIL, GAP]

    def test_one_type_twice_is_one_need(self):
        assert needed_meters(template(), [item(HOURS), item(OIL), item(HOURS)]) == [HOURS, OIL]

    def test_both_trigger_kind(self):
        assert needed_meters(template("both"), [item(OIL)]) == [HOURS, OIL]

    def test_a_tick_left_in_the_row_changes_nothing(self):
        # A1.3: the tick is gone; a row that still carries the old column is read for its type only
        assert needed_meters({**template(), "meter_from_parent": 1}, []) == [HOURS]


class TestResolveMeters:

    NODE_ID = 5

    def test_the_own_meter_first(self):
        types = {5: {HOURS}, 4: {HOURS}}
        assert resolve_meters([HOURS], self.NODE_ID, types, {HOURS: 4}) == {HOURS: 5}

    def test_the_link_in_use_when_the_node_has_no_meter(self):
        types = {5: set(), 4: {HOURS}}
        assert resolve_meters([HOURS], self.NODE_ID, types, {}) == {HOURS: None}
        assert resolve_meters([HOURS], self.NODE_ID, types, {HOURS: 4}) == {HOURS: 4}

    def test_each_type_its_own_link(self):
        types = {5: set(), 4: {OIL}, 3: {HOURS}}
        assert resolve_meters([HOURS, OIL], self.NODE_ID, types, {HOURS: 3, OIL: 4}) == {HOURS: 3, OIL: 4}

    def test_nothing_walks_up_without_a_link(self):
        assert resolve_meters([GAP], self.NODE_ID, {4: {GAP}, 3: {GAP}}, {}) == {GAP: None}

    def test_no_needs(self):
        assert resolve_meters([], self.NODE_ID, {5: {HOURS}}, {}) == {}


class TestApplies:

    def test_every_need_resolved(self):
        assert applies([HOURS, OIL], {HOURS: 5, OIL: 4}) == []

    def test_the_missing_types_in_the_template_order(self):
        assert applies([OIL, HOURS, GAP], {OIL: None, HOURS: 5, GAP: None}) == [OIL, GAP]

    def test_no_needs_always_applies(self):
        assert applies([], {}) == []


class TestStopRemark:

    def test_in_force(self):
        assert stop_remark(True, True, False, [], "HP003") is None

    def test_the_order_of_the_reasons(self):
        assert stop_remark(False, False, True, ["Run hours"], "HP003", "Sold") == TEMPLATE_INACTIVE_REMARK
        assert stop_remark(True, False, True, ["Run hours"], "HP003", "Sold") == UNLINKED_REMARK
        assert stop_remark(True, True, True, ["Run hours"], "HP003", "Hand-greased") == (
            "Not for this machine: Hand-greased")
        assert stop_remark(True, True, False, ["Run hours"], "HP003") == (
            "Does not apply: no Run hours meter on HP003.")

    def test_two_and_three_missing_types(self):
        assert stop_remark(True, True, False, ["Run hours", "Oil temperature"], "HP003") == (
            "Does not apply: no Run hours or Oil temperature meter on HP003.")
        assert missing_text(["A", "B", "C"], "EOT03") == "no A, B or C meter on EOT03"

    def test_the_words_of_one(self):
        assert missing_text(["Brake air gap"], "EOT03") == "no Brake air gap meter on EOT03"

    def test_a_bad_flag_is_a_shell_bug(self):
        with pytest.raises(TypeError):
            stop_remark(1, True, False, [], "HP003")
