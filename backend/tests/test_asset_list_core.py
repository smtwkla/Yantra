"""Printable asset list — the pure core (S015)."""

import asset_list_core as core
from asset_list_core import TOO_MANY_ROWS, build_asset_list


def machine(id_, code, site="S1", unit="U1", **extra):
    return {"id": id_, "code": code, "site_code": site, "site_name": f"{site} name",
            "unit_code": unit, "unit_name": f"{unit} name", **extra}


def part(id_, parent_id, code, lifecycle="in_service"):
    return {"id": id_, "parent_id": parent_id, "code": code, "lifecycle": lifecycle}


def codes(unit):
    return [r["code"] for r in unit["rows"]]


def test_empty_input_gives_no_units():
    assert build_asset_list([], [], False) == ({"units": [], "total_rows": 0}, None)


def test_units_ordered_by_site_then_unit_and_machines_by_code():
    result, _ = build_asset_list([machine(1, "B2", "S2", "U1"), machine(2, "A2", "S1", "U2"),
                                  machine(3, "C1", "S1", "U1"), machine(4, "A1", "S1", "U1")], [], False)
    assert [(u["site_code"], u["unit_code"]) for u in result["units"]] == [("S1", "U1"), ("S1", "U2"), ("S2", "U1")]
    assert codes(result["units"][0]) == ["A1", "C1"]
    assert result["units"][0]["unit_name"] == "U1 name"


def test_parts_follow_their_machine_depth_first_by_code():
    machines = [machine(1, "M1"), machine(2, "M2")]
    parts = [part(13, 1, "CU2"), part(11, 1, "CU1"), part(21, 11, "C2"), part(20, 11, "C1"),
             part(30, 2, "X1")]
    result, _ = build_asset_list(machines, parts, False)
    rows = result["units"][0]["rows"]
    assert [(r["code"], r["depth"]) for r in rows] == [
        ("M1", 0), ("CU1", 1), ("C1", 2), ("C2", 2), ("CU2", 1), ("M2", 0), ("X1", 1)]


def test_number_counts_machines_only():
    result, _ = build_asset_list([machine(1, "M1"), machine(2, "M2")], [part(11, 1, "CU1")], False)
    assert [r["number"] for r in result["units"][0]["rows"]] == [1, None, 2]


def test_number_restarts_in_each_unit():
    result, _ = build_asset_list([machine(1, "M1", unit="U1"), machine(2, "M2", unit="U2")], [], False)
    assert [u["rows"][0]["number"] for u in result["units"]] == [1, 1]


def test_scrapped_parts_dropped_unless_included():
    parts = [part(11, 1, "CU1", "scrapped"), part(12, 1, "CU2")]
    dropped, _ = build_asset_list([machine(1, "M1")], parts, False)
    kept, _ = build_asset_list([machine(1, "M1")], parts, True)
    assert codes(dropped["units"][0]) == ["M1", "CU2"]
    assert codes(kept["units"][0]) == ["M1", "CU1", "CU2"]


def test_children_of_a_scrapped_part_go_with_it():
    parts = [part(11, 1, "CU1", "scrapped"), part(21, 11, "C1")]
    result, _ = build_asset_list([machine(1, "M1")], parts, False)
    assert codes(result["units"][0]) == ["M1"]


def test_part_without_its_machine_is_ignored():
    result, _ = build_asset_list([machine(1, "M1")], [part(99, 98, "ORPHAN")], False)
    assert codes(result["units"][0]) == ["M1"]


def test_counts_per_unit_and_total():
    result, _ = build_asset_list([machine(1, "M1"), machine(2, "M2"), machine(3, "M3", unit="U2")],
                                 [part(11, 1, "CU1"), part(21, 11, "C1")], False)
    first, second = result["units"]
    assert (first["machine_count"], first["part_count"]) == (2, 2)
    assert (second["machine_count"], second["part_count"]) == (1, 0)
    assert result["total_rows"] == 5


def test_extra_fields_pass_through():
    result, _ = build_asset_list([machine(1, "M1", serial_no="SN1")], [], False)
    assert result["units"][0]["rows"][0]["serial_no"] == "SN1"


def test_total_after_parts_over_the_cap_is_refused(monkeypatch):
    monkeypatch.setattr(core, "MAX_ASSET_LIST_ROWS", 3)
    assert build_asset_list([machine(1, "M1"), machine(2, "M2"), machine(3, "M3")], [], False)[0] is not None
    result, message = build_asset_list([machine(1, "M1"), machine(2, "M2")],
                                       [part(11, 1, "CU1"), part(12, 2, "CU2")], False)
    assert (result, message) == (None, TOO_MANY_ROWS)
