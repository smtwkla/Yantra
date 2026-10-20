"""Printable asset list endpoint (S015), against the test DB."""

import re

import pytest

import asset_list_core

EQUIPMENT = "/api/equipment"
ASSET_LIST = f"{EQUIPMENT}/asset-list"


def _get(client, **query):
    return client.get(ASSET_LIST, query_string=query)


def _rows(res):
    assert res.status_code == 200, res.get_json()
    return [r for unit in res.get_json()["units"] for r in unit["rows"]]


def _codes(res):
    return [r["code"] for r in _rows(res)]


def _scrap(admin, node):
    assert admin.put(f"{EQUIPMENT}/{node['id']}", json={"status": "scrapped"}).status_code == 200


@pytest.fixture
def tree(make_equipment, unit):
    """A press with a gearbox (holding a seal and a bearing) and a motor, in ``unit``."""
    press = make_equipment(unit=unit)
    gearbox = make_equipment(parent=press, name="Gearbox")
    motor = make_equipment(parent=press, name="Motor")
    seal = make_equipment(parent=gearbox, level="component", name="Seal")
    bearing = make_equipment(parent=gearbox, level="component", name="Bearing")
    return {"press": press, "gearbox": gearbox, "motor": motor, "seal": seal, "bearing": bearing}


class TestFilters:

    def test_the_row_fields_and_unit_header(self, admin, make_equipment, unit):
        node = make_equipment(unit=unit, serial_no="SN-1", year=2019)
        body = _get(admin, unit_id=unit["id"]).get_json()
        (group,) = body["units"]
        assert (group["unit_code"], group["unit_name"], group["machine_count"]) == (unit["code"], unit["name"], 1)
        row = group["rows"][0]
        assert (row["id"], row["code"], row["serial_no"], row["year"], row["depth"], row["number"]) == (
            node["id"], node["code"], "SN-1", 2019, 0, 1)
        assert body["total_rows"] == 1

    def test_unit_and_site(self, admin, make_equipment, make_unit, make_site):
        site = make_site()
        in_unit, other = make_unit(site=site), make_unit(site=site)
        a, b = make_equipment(unit=in_unit), make_equipment(unit=other)
        assert _codes(_get(admin, unit_id=in_unit["id"])) == [a["code"]]
        assert sorted(_codes(_get(admin, site_id=site["id"]))) == sorted([a["code"], b["code"]])

    def test_class_status_criticality(self, admin, make_equipment, make_class, unit):
        cls = make_class()
        a = make_equipment(unit=unit, cls=cls, criticality="A")
        b = make_equipment(unit=unit, criticality="C")
        assert _codes(_get(admin, unit_id=unit["id"], class_id=cls["id"])) == [a["code"]]
        assert _codes(_get(admin, unit_id=unit["id"], criticality="C")) == [b["code"]]
        assert admin.put(f"{EQUIPMENT}/{b['id']}", json={"status": "standby"}).status_code == 200
        assert _codes(_get(admin, unit_id=unit["id"], status="standby")) == [b["code"]]

    def test_scrapped_machines_only_when_included(self, admin, make_equipment, unit):
        node = make_equipment(unit=unit)
        _scrap(admin, node)
        assert _codes(_get(admin, unit_id=unit["id"])) == []
        assert _codes(_get(admin, unit_id=unit["id"], include_scrapped=1)) == [node["code"]]

    def test_a_bad_filter_is_400_with_its_field(self, admin):
        res = _get(admin, status="nope")
        assert res.status_code == 400
        assert res.get_json()["field"] == "status"

    def test_machines_only_without_parts(self, admin, tree, unit):
        assert _codes(_get(admin, unit_id=unit["id"])) == [tree["press"]["code"]]


class TestParts:

    def test_parts_come_with_their_machine_whatever_their_class(self, admin, tree, unit):
        # the class filter picks the press's class; the parts are of other classes
        res = _get(admin, unit_id=unit["id"], class_id=tree["press"]["class_id"], with_parts=1)
        rows = _rows(res)
        assert {r["id"] for r in rows} == {n["id"] for n in tree.values()}
        assert [r["depth"] for r in rows if r["id"] == tree["press"]["id"]] == [0]
        assert rows[0]["number"] == 1 and all(r["number"] is None for r in rows[1:])
        assert res.get_json()["units"][0]["part_count"] == 4
        assert res.get_json()["total_rows"] == 5

    def test_parts_sit_under_their_parent_depth_first(self, admin, tree, unit):
        rows = _rows(_get(admin, unit_id=unit["id"], with_parts=1))
        depth_of = {r["id"]: r["depth"] for r in rows}
        assert depth_of[tree["gearbox"]["id"]] == depth_of[tree["motor"]["id"]] == 1
        assert depth_of[tree["seal"]["id"]] == depth_of[tree["bearing"]["id"]] == 2
        position = {r["id"]: i for i, r in enumerate(rows)}
        assert position[tree["press"]["id"]] == 0
        # the gearbox's components follow the gearbox directly, before the next component unit
        low, high = sorted((position[tree["seal"]["id"]], position[tree["bearing"]["id"]]))
        assert position[tree["gearbox"]["id"]] + 1 == low and high == low + 1

    def test_a_component_fitted_directly_to_the_machine_is_depth_1(self, admin, make_equipment, unit):
        press = make_equipment(unit=unit)
        motor = make_equipment(parent=press, level="component", name="Motor")
        rows = _rows(_get(admin, unit_id=unit["id"], with_parts=1))
        assert [(r["id"], r["depth"]) for r in rows] == [(press["id"], 0), (motor["id"], 1)]

    def test_scrapped_parts_left_out_unless_included(self, admin, tree, unit):
        _scrap(admin, tree["bearing"])
        without = _codes(_get(admin, unit_id=unit["id"], with_parts=1))
        with_scrapped = _codes(_get(admin, unit_id=unit["id"], with_parts=1, include_scrapped=1))
        assert tree["bearing"]["code"] not in without and len(without) == 4
        assert tree["bearing"]["code"] in with_scrapped and len(with_scrapped) == 5

    def test_no_machines_with_parts_on_is_empty(self, admin, unit):
        res = _get(admin, unit_id=unit["id"], with_parts=1)
        assert res.status_code == 200
        assert (res.get_json()["units"], res.get_json()["total_rows"]) == ([], 0)


class TestUnitAccess:

    def test_a_user_sees_only_their_units(self, user_with_units, make_equipment, make_unit):
        mine, theirs = make_unit(), make_unit()
        a = make_equipment(unit=mine)
        make_equipment(unit=theirs)
        engineer = user_with_units("maint_engineer", [mine])
        assert _codes(_get(engineer)) == [a["code"]]

    def test_a_user_with_no_units_gets_an_empty_result(self, user_with_units, node):
        engineer = user_with_units("maint_engineer", [])
        res = _get(engineer, with_parts=1)
        assert res.status_code == 200
        assert (res.get_json()["units"], res.get_json()["total_rows"]) == ([], 0)

    @pytest.mark.parametrize("role", ["admin", "it_admin"])
    def test_all_units_roles_see_the_unit(self, user_with_units, node, unit, role):
        assert node["code"] in _codes(_get(user_with_units(role, []), unit_id=unit["id"]))


class TestCapAndStamp:

    def test_machines_over_the_cap_are_400(self, admin, make_equipment, unit, monkeypatch):
        make_equipment(unit=unit)
        make_equipment(unit=unit)
        monkeypatch.setattr(asset_list_core, "MAX_ASSET_LIST_ROWS", 1)
        res = _get(admin, unit_id=unit["id"])
        assert (res.status_code, res.get_json()["error"]) == (400, asset_list_core.TOO_MANY_ROWS)

    def test_total_after_parts_over_the_cap_is_400(self, admin, tree, unit, monkeypatch):
        monkeypatch.setattr(asset_list_core, "MAX_ASSET_LIST_ROWS", 3)
        assert _get(admin, unit_id=unit["id"]).status_code == 200   # one machine: under the cap
        res = _get(admin, unit_id=unit["id"], with_parts=1)         # five rows: over it
        assert (res.status_code, res.get_json()["error"]) == (400, asset_list_core.TOO_MANY_ROWS)

    def test_printed_stamp(self, admin, unit):
        body = _get(admin, unit_id=unit["id"]).get_json()
        assert body["printed_by"]
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+05:30", body["printed_at"])
