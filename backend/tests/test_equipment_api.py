"""Equipment register API — the equipment tree, codes, status, events and unit access,
against the test DB (needs the dev MariaDB container, tooling/dev/dev-db-up.bat).

Codes are asserted relative to the first one issued in a fresh class (n, n+1), never
as absolute numbers.  Unit-access tests each use a fresh username.
"""

import pymysql
import pytest

import api_common
import config
import equipment
from local_db import get_local_db

MASTERS = "/api/masters"
EQUIPMENT = "/api/equipment"


def _number(node, cls):
    """The counter part of a code: VBM007 in class VBM -> 7."""
    assert node["code"].startswith(cls["code"])
    return int(node["code"][len(cls["code"]):])


def _get(client, node):
    res = client.get(f"{EQUIPMENT}/{node['id']}")
    assert res.status_code == 200, res.get_json()
    return res.get_json()


def _put(client, node, **body):
    return client.put(f"{EQUIPMENT}/{node['id']}", json=body)


def _events(client, node):
    return [(e["event"], e["old_value"], e["new_value"]) for e in _get(client, node)["events"]]


def _list(client, **params):
    res = client.get(EQUIPMENT, query_string=params)
    assert res.status_code == 200, res.get_json()
    return res.get_json()


def _ids(client, **params):
    return [item["id"] for item in _list(client, **params)["items"]]


def _db(sql, params=()):
    conn = get_local_db(config.DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()
    finally:
        conn.close()


class TestCodes:

    def test_each_level_gets_the_next_code_of_its_class(self, make_class, make_equipment):
        cls = make_class()
        mill = make_equipment(cls=cls)
        drive = make_equipment(parent=mill, cls=cls)
        motor = make_equipment(parent=drive, level="component", cls=cls)
        n = _number(mill, cls)
        assert mill["code"] == f"{cls['code']}{n:03d}"
        assert [_number(drive, cls), _number(motor, cls)] == [n + 1, n + 2]
        assert (mill["level"], drive["level"], motor["level"]) == ("equipment", "component_unit", "component")

    def test_two_classes_have_independent_counters(self, make_class, make_equipment):
        cls_a, cls_b = make_class(), make_class()
        a1 = make_equipment(cls=cls_a)
        b1 = make_equipment(cls=cls_b)
        a2 = make_equipment(cls=cls_a)
        assert _number(a2, cls_a) == _number(a1, cls_a) + 1
        assert b1["code"].startswith(cls_b["code"])

    def test_refused_creates_use_no_number(self, admin, make_class, make_unit, make_equipment):
        cls = make_class()
        first = make_equipment(cls=cls)
        unit, inactive = make_unit(), make_unit()
        admin.put(f"{MASTERS}/units/{inactive['id']}", json={"active": False})
        refused_400 = admin.post(EQUIPMENT, json={"level": "equipment", "unit_id": unit["id"], "class_id": cls["id"]})
        refused_409 = admin.post(EQUIPMENT, json={"level": "equipment", "unit_id": inactive["id"],
                                                  "class_id": cls["id"], "name": "x"})
        assert (refused_400.status_code, refused_409.status_code) == (400, 409)
        assert _number(make_equipment(cls=cls), cls) == _number(first, cls) + 1

    def test_a_failure_after_the_counter_bump_rolls_it_back(self, admin, make_class, make_unit, make_equipment,
                                                            monkeypatch):
        cls = make_class()
        first = make_equipment(cls=cls)
        unit = make_unit()

        def fail(*args):
            raise RuntimeError("forced")
        monkeypatch.setattr(equipment, "_write_events", fail)
        with pytest.raises(RuntimeError):
            admin.post(EQUIPMENT, json={"level": "equipment", "unit_id": unit["id"], "class_id": cls["id"],
                                        "name": "x"})
        monkeypatch.undo()
        assert _number(make_equipment(cls=cls), cls) == _number(first, cls) + 1

    def test_created_event_holds_the_full_path(self, admin, make_unit, make_equipment):
        unit = make_unit()
        node = make_equipment(unit=unit)
        assert node["full_path"] == f"{unit['full_code']}.{node['code']}"
        assert _events(admin, node) == [("created", None, node["full_path"])]

    def test_code_in_the_body_is_ignored(self, admin, make_unit, make_class):
        cls, unit = make_class(), make_unit()
        res = admin.post(EQUIPMENT, json={"level": "equipment", "unit_id": unit["id"], "class_id": cls["id"],
                                          "name": "x", "code": "ZZ999"})
        assert res.status_code == 201
        assert res.get_json()["code"].startswith(cls["code"])

    def test_duplicate_code_maps_to_409_without_field(self, admin, make_class, make_unit, make_equipment):
        cls = make_class()
        make_equipment(cls=cls)
        # A counter behind the codes in use (never happens through the API) collides on the UNIQUE key
        _db("UPDATE serial_counters SET last_value = 0 WHERE scope = %s", (f"EQ:{cls['code']}",))
        res = admin.post(EQUIPMENT, json={"level": "equipment", "unit_id": make_unit()["id"],
                                          "class_id": cls["id"], "name": "x"})
        assert res.status_code == 409
        assert res.get_json() == {"error": "Code collision — retry"}


class TestTree:

    def test_detail_has_ancestors_children_and_paths(self, admin, make_unit, make_equipment):
        unit = make_unit()
        mill = make_equipment(unit=unit, name="Mill")
        drive = make_equipment(parent=mill, name="Drive")
        motor = make_equipment(parent=drive, level="component", name="Motor")
        guard = make_equipment(parent=mill, level="component", name="Guard")
        assert motor["full_path"] == f"{unit['full_code']}.{mill['code']}.{drive['code']}.{motor['code']}"
        assert motor["unit_id"] == unit["id"] and motor["unit"] == unit["full_code"]
        assert [a["id"] for a in motor["ancestors"]] == [mill["id"], drive["id"]]
        assert set(motor["ancestors"][0]) == {"id", "code", "level", "name"}
        detail = _get(admin, mill)
        children = {c["id"]: c for c in detail["children"]}
        assert set(children) == {drive["id"], guard["id"]}
        assert [g["id"] for g in children[drive["id"]]["children"]] == [motor["id"]]
        assert children[guard["id"]]["children"] == []
        assert detail["ancestors"] == []

    @pytest.mark.parametrize("parent_level, child_level", [
        ("component_unit", "component_unit"), ("component", "component"), ("component", "component_unit"),
    ])
    def test_wrong_parent_level_is_400(self, admin, make_equipment, make_class, parent_level, child_level):
        mill = make_equipment()
        parent = make_equipment(parent=mill, level=parent_level)
        res = admin.post(EQUIPMENT, json={"level": child_level, "parent_id": parent["id"],
                                          "class_id": make_class()["id"], "name": "x"})
        assert res.status_code == 400
        assert res.get_json()["field"] == "parent_id"

    def test_unit_on_a_part_or_no_unit_on_equipment_is_400(self, admin, make_equipment, make_unit, make_class):
        mill, cls = make_equipment(), make_class()
        part = admin.post(EQUIPMENT, json={"level": "component", "parent_id": mill["id"],
                                           "unit_id": make_unit()["id"], "class_id": cls["id"], "name": "x"})
        assert (part.status_code, part.get_json()["field"]) == (400, "unit_id")
        bare = admin.post(EQUIPMENT, json={"level": "equipment", "class_id": cls["id"], "name": "x"})
        assert (bare.status_code, bare.get_json()["field"]) == (400, "unit_id")

    def test_the_check_constraint_holds_when_the_shell_is_bypassed(self, make_equipment):
        mill = make_equipment()
        row = _db("SELECT unit_id, class_id FROM equipment WHERE id = %s", (mill["id"],))[0]
        with pytest.raises(pymysql.err.OperationalError) as caught:
            _db("INSERT INTO equipment (code, level, unit_id, class_id, name, created_by) "
                "VALUES ('ZZCHK1', 'component', %s, %s, 'x', 'test')", (row["unit_id"], row["class_id"]))
        assert caught.value.args[0] == 4025
        with pytest.raises(pymysql.err.OperationalError):
            _db("INSERT INTO equipment (code, level, parent_id, unit_id, class_id, name, created_by) "
                "VALUES ('ZZCHK2', 'equipment', %s, %s, %s, 'x', 'test')",
                (mill["id"], row["unit_id"], row["class_id"]))


class TestUnknownIdsAndImmutableFields:

    @pytest.mark.parametrize("field", ["unit_id", "class_id"])
    def test_unknown_id_on_create_equipment_is_400(self, admin, make_unit, make_class, field):
        body = {"level": "equipment", "unit_id": make_unit()["id"], "class_id": make_class()["id"],
                "name": "x", field: 999999}
        res = admin.post(EQUIPMENT, json=body)
        assert (res.status_code, res.get_json()["field"]) == (400, field)

    def test_unknown_parent_on_create_is_400(self, admin, make_class):
        res = admin.post(EQUIPMENT, json={"level": "component", "parent_id": 999999,
                                          "class_id": make_class()["id"], "name": "x"})
        assert (res.status_code, res.get_json()["field"]) == (400, "parent_id")

    def test_unknown_ids_on_update_are_400(self, admin, make_equipment):
        mill = make_equipment()
        part = make_equipment(parent=mill)
        for node, field in ((mill, "unit_id"), (mill, "class_id"), (part, "parent_id")):
            res = _put(admin, node, **{field: 999999})
            assert (res.status_code, res.get_json()["field"]) == (400, field)

    def test_changed_code_or_level_is_400(self, admin, make_equipment):
        mill = make_equipment()
        assert _put(admin, mill, code="ZZ001").get_json()["field"] == "code"
        assert _put(admin, mill, level="component").get_json()["field"] == "level"

    def test_unchanged_code_and_level_are_accepted(self, admin, make_equipment):
        mill = make_equipment()
        res = _put(admin, mill, code=mill["code"].lower(), level="equipment", name="Renamed")
        assert res.status_code == 200
        assert res.get_json()["name"] == "Renamed"

    def test_unknown_node_is_404(self, admin):
        assert admin.get(f"{EQUIPMENT}/999999").status_code == 404
        assert admin.put(f"{EQUIPMENT}/999999", json={"name": "x"}).status_code == 404

    def test_body_must_be_an_object(self, admin, make_equipment):
        mill = make_equipment()
        assert admin.put(f"{EQUIPMENT}/{mill['id']}", json=[1]).status_code == 400
        assert admin.post(EQUIPMENT, json=[1]).status_code == 400


class TestReclassify:

    def test_code_unchanged_and_class_event(self, admin, make_class, make_equipment):
        old_cls, new_cls = make_class(), make_class()
        mill = make_equipment(cls=old_cls)
        res = _put(admin, mill, class_id=new_cls["id"])
        assert res.status_code == 200
        body = res.get_json()
        assert body["code"] == mill["code"]
        assert (body["class_id"], body["class_code"]) == (new_cls["id"], new_cls["code"])
        assert _events(admin, mill)[0] == ("class", old_cls["code"], new_cls["code"])

    def test_to_an_inactive_class_is_409(self, admin, make_class, make_equipment):
        mill, cls = make_equipment(), make_class()
        admin.put(f"{MASTERS}/equipment-classes/{cls['id']}", json={"active": False})
        res = _put(admin, mill, class_id=cls["id"])
        assert (res.status_code, res.get_json()["field"]) == (409, "class_id")

    def test_create_with_an_inactive_class_is_409(self, admin, make_class, make_unit):
        cls = make_class()
        admin.put(f"{MASTERS}/equipment-classes/{cls['id']}", json={"active": False})
        res = admin.post(EQUIPMENT, json={"level": "equipment", "unit_id": make_unit()["id"],
                                          "class_id": cls["id"], "name": "x"})
        assert (res.status_code, res.get_json()["field"]) == (409, "class_id")

    def test_existing_equipment_keeps_a_deactivated_class(self, admin, make_class, make_equipment):
        cls = make_class()
        mill = make_equipment(cls=cls)
        admin.put(f"{MASTERS}/equipment-classes/{cls['id']}", json={"active": False})
        assert _put(admin, mill, name="Still editable", class_id=cls["id"]).status_code == 200


class TestMoveEquipment:

    def test_one_moved_unit_event_and_the_parts_follow(self, admin, make_unit, make_equipment):
        unit_a, unit_b = make_unit(), make_unit()
        mill = make_equipment(unit=unit_a)
        drive = make_equipment(parent=mill)
        motor = make_equipment(parent=drive, level="component")
        res = _put(admin, mill, unit_id=unit_b["id"])
        assert res.status_code == 200
        new_path = f"{unit_b['full_code']}.{mill['code']}"
        assert res.get_json()["full_path"] == new_path
        assert _events(admin, mill)[0] == ("moved_unit", mill["full_path"], new_path)
        assert _get(admin, motor)["full_path"] == f"{new_path}.{drive['code']}.{motor['code']}"
        assert _get(admin, motor)["unit_id"] == unit_b["id"]
        # The parts get no event of their own
        assert [e[0] for e in _events(admin, drive)] == ["created"]

    def test_to_an_inactive_unit_is_409(self, admin, make_unit, make_equipment):
        mill, target = make_equipment(), make_unit()
        admin.put(f"{MASTERS}/units/{target['id']}", json={"active": False})
        res = _put(admin, mill, unit_id=target["id"])
        assert (res.status_code, res.get_json()["field"]) == (409, "unit_id")

    def test_same_unit_is_not_a_move(self, admin, make_unit, make_equipment):
        unit = make_unit()
        mill = make_equipment(unit=unit)
        assert _put(admin, mill, unit_id=unit["id"]).status_code == 200
        assert [e[0] for e in _events(admin, mill)] == ["created"]


class TestReparent:

    def test_a_component_moves_to_another_component_unit(self, admin, make_equipment):
        mill = make_equipment()
        drive_a, drive_b = make_equipment(parent=mill), make_equipment(parent=mill)
        motor = make_equipment(parent=drive_a, level="component")
        res = _put(admin, motor, parent_id=drive_b["id"])
        assert res.status_code == 200
        assert res.get_json()["parent_id"] == drive_b["id"]
        assert _events(admin, motor)[0] == ("moved_parent", motor["full_path"], res.get_json()["full_path"])

    def test_a_component_unit_moves_with_its_components(self, admin, make_unit, make_equipment):
        mill_a, mill_b = make_equipment(), make_equipment()
        drive = make_equipment(parent=mill_a)
        motor = make_equipment(parent=drive, level="component")
        assert _put(admin, drive, parent_id=mill_b["id"]).status_code == 200
        moved = _get(admin, motor)
        assert moved["full_path"] == f"{mill_b['full_path']}.{drive['code']}.{motor['code']}"
        assert [a["id"] for a in moved["ancestors"]] == [mill_b["id"], drive["id"]]

    def test_a_cross_unit_reparent_writes_one_moved_parent_event(self, admin, make_unit, make_equipment):
        mill_a, mill_b = make_equipment(unit=make_unit()), make_equipment(unit=make_unit())
        guard = make_equipment(parent=mill_a, level="component")
        res = _put(admin, guard, parent_id=mill_b["id"])
        assert res.get_json()["unit_id"] == mill_b["unit_id"]
        events = _events(admin, guard)
        assert events[0] == ("moved_parent", guard["full_path"], f"{mill_b['full_path']}.{guard['code']}")
        assert [e[0] for e in events] == ["moved_parent", "created"]

    def test_into_a_scrapped_parent_is_409(self, admin, make_equipment):
        mill = make_equipment()
        old_drive = make_equipment(parent=mill)
        motor = make_equipment(parent=old_drive, level="component")
        dead_drive = make_equipment(parent=mill)
        assert _put(admin, dead_drive, status="scrapped").status_code == 200
        res = _put(admin, motor, parent_id=dead_drive["id"])
        assert (res.status_code, res.get_json()["field"]) == (409, "parent_id")

    def test_wrong_level_target_is_400(self, admin, make_equipment):
        mill = make_equipment()
        drive_a, drive_b = make_equipment(parent=mill), make_equipment(parent=mill)
        res = _put(admin, drive_a, parent_id=drive_b["id"])
        assert (res.status_code, res.get_json()["field"]) == (400, "parent_id")


class TestStatus:

    @pytest.mark.parametrize("old, new", [
        ("in_service", "standby"), ("in_service", "out_of_use"), ("standby", "in_service"),
        ("standby", "out_of_use"), ("out_of_use", "in_service"), ("out_of_use", "standby"),
    ])
    def test_every_allowed_change(self, admin, make_equipment, old, new):
        node = make_equipment(status=old)
        assert node["status"] == old
        res = _put(admin, node, status=new)
        assert (res.status_code, res.get_json()["status"]) == (200, new)
        assert _events(admin, node)[0] == ("status", old, new)

    def test_created_scrapped_is_400(self, admin, make_unit, make_class):
        res = admin.post(EQUIPMENT, json={"level": "equipment", "unit_id": make_unit()["id"],
                                          "class_id": make_class()["id"], "name": "x", "status": "scrapped"})
        assert (res.status_code, res.get_json()["field"]) == (400, "status")

    def test_scrapping_with_live_parts_is_409(self, admin, make_equipment):
        mill = make_equipment()
        drive = make_equipment(parent=mill)
        motor = make_equipment(parent=drive, level="component")
        for node in (mill, drive):
            res = _put(admin, node, status="scrapped")
            assert res.status_code == 409
            assert res.get_json() == {"error": "Scrap or move its parts first", "field": "status"}
        assert _put(admin, motor, status="scrapped").status_code == 200
        # The grandchild is scrapped now, but the child is not
        assert _put(admin, mill, status="scrapped").status_code == 409
        assert _put(admin, drive, status="scrapped").status_code == 200
        assert _put(admin, mill, status="scrapped").status_code == 200

    def test_a_live_grandchild_blocks_scrapping(self, admin, make_equipment):
        mill = make_equipment()
        drive = make_equipment(parent=mill)
        make_equipment(parent=drive, level="component")
        # Force the child to scrapped directly, so only the grandchild is live
        _db("UPDATE equipment SET status = 'scrapped' WHERE id = %s", (drive["id"],))
        assert _put(admin, mill, status="scrapped").status_code == 409

    def test_any_put_on_a_scrapped_node_is_409(self, admin, make_equipment):
        node = make_equipment()
        assert _put(admin, node, status="scrapped").status_code == 200
        for body in ({"name": "x"}, {"status": "in_service"}, {}):
            res = _put(admin, node, **body)
            assert res.status_code == 409
            assert res.get_json() == {"error": "This record is scrapped and cannot be changed"}

    def test_a_scrapped_node_is_no_create_target(self, admin, make_equipment, make_class):
        mill = make_equipment()
        assert _put(admin, mill, status="scrapped").status_code == 200
        res = admin.post(EQUIPMENT, json={"level": "component", "parent_id": mill["id"],
                                          "class_id": make_class()["id"], "name": "x"})
        assert (res.status_code, res.get_json()["field"]) == (409, "parent_id")

    def test_scrapping_with_a_name_change_applies_both(self, admin, make_equipment):
        node = make_equipment()
        res = _put(admin, node, status="scrapped", name="Old mill")
        assert res.status_code == 200
        assert (res.get_json()["status"], res.get_json()["name"]) == ("scrapped", "Old mill")

    def test_a_scrapped_part_stays_on_its_parents_page(self, admin, make_equipment):
        mill = make_equipment()
        drive = make_equipment(parent=mill)
        _put(admin, drive, status="scrapped")
        children = _get(admin, mill)["children"]
        assert [(c["id"], c["status"]) for c in children] == [(drive["id"], "scrapped")]
        assert _get(admin, drive)["status"] == "scrapped"

    def test_a_part_has_its_own_status(self, admin, make_equipment):
        mill = make_equipment()
        motor = make_equipment(parent=mill, level="component")
        assert _put(admin, motor, status="scrapped").status_code == 200
        assert _get(admin, mill)["status"] == "in_service"


class TestEvents:

    def test_one_event_per_changed_tracked_field(self, admin, make_class, make_equipment):
        mill, cls = make_equipment(), make_class()
        _put(admin, mill, class_id=cls["id"], criticality="A", status="standby", name="Renamed")
        events = _events(admin, mill)
        assert sorted(events[:3]) == sorted([
            ("class", mill["class_code"], cls["code"]), ("criticality", "C", "A"), ("status", "in_service", "standby"),
        ])
        assert len(events) == 4

    def test_untracked_edits_write_no_event(self, admin, make_equipment):
        mill = make_equipment()
        res = _put(admin, mill, name="New", make="Make", model="M1", serial_no="SN-1", year=2020)
        assert res.status_code == 200
        body = res.get_json()
        assert (body["make"], body["model"], body["serial_no"], body["year"]) == ("Make", "M1", "SN-1", 2020)
        assert body["updated_by"] == "test_it_admin"
        assert [e[0] for e in _events(admin, mill)] == ["created"]

    def test_inherited_grade_change_writes_no_event_on_the_part(self, admin, make_equipment):
        mill = make_equipment(criticality="B")
        motor = make_equipment(parent=mill, level="component")
        assert motor["effective_criticality"] == "B"
        _put(admin, mill, criticality="A")
        assert _get(admin, motor)["effective_criticality"] == "A"
        assert [e[0] for e in _events(admin, motor)] == ["created"]

    def test_criticality_events_show_inherit(self, admin, make_equipment):
        mill = make_equipment()
        motor = make_equipment(parent=mill, level="component")
        _put(admin, motor, criticality="A")
        _put(admin, motor, criticality=None)
        assert _events(admin, motor)[:2] == [("criticality", "A", "inherit"), ("criticality", "inherit", "A")]

    def test_a_forced_rollback_leaves_no_event_and_no_change(self, admin, make_equipment, monkeypatch):
        mill = make_equipment()
        real = equipment._write_events

        def write_then_fail(cur, equipment_id, changes):
            real(cur, equipment_id, changes)
            raise RuntimeError("forced after the events were written")
        monkeypatch.setattr(equipment, "_write_events", write_then_fail)
        with pytest.raises(RuntimeError):
            _put(admin, mill, status="standby")
        monkeypatch.undo()
        assert _get(admin, mill)["status"] == "in_service"
        assert [e[0] for e in _events(admin, mill)] == ["created"]

    def test_newest_first(self, admin, make_equipment):
        mill = make_equipment()
        _put(admin, mill, status="standby")
        _put(admin, mill, status="out_of_use")
        events = _get(admin, mill)["events"]
        assert [e["event"] for e in events] == ["status", "status", "created"]
        assert [e["new_value"] for e in events[:2]] == ["out_of_use", "standby"]
        assert events[0]["created_by"] == "test_it_admin"
        assert events[0]["created_at"].endswith("+05:30")


@pytest.fixture
def stale_reread(monkeypatch):
    """Simulate a snapshot older than a commit made while the write waited for a lock (CR1-01):
    once the INSERT or UPDATE has run, every plain read of a node returns ``change(row)``."""
    def install(change):
        written = []
        real_read = equipment._read_node

        def read(cur, node_id):
            row = real_read(cur, node_id)
            return change(row) if written else row
        for name in ("insert_row", "update_row"):
            def write(*args, _real=getattr(equipment, name)):
                result = _real(*args)
                written.append(True)
                return result
            monkeypatch.setattr(equipment, name, write)
        monkeypatch.setattr(equipment, "_read_node", read)
    return install


class TestRereadAfterWrite:
    """CR1-01: the plain re-read after a write runs on the transaction's snapshot."""

    RETRY = {"error": "This record changed while saving — try again"}

    def test_create_that_cannot_read_back_is_409_and_rolls_back(self, admin, make_class, make_unit,
                                                                make_equipment, stale_reread, monkeypatch):
        cls, unit = make_class(), make_unit()
        first = make_equipment(cls=cls)
        stale_reread(lambda row: None)
        res = admin.post(EQUIPMENT, json={"level": "equipment", "unit_id": unit["id"], "class_id": cls["id"],
                                          "name": "x"})
        monkeypatch.undo()
        assert (res.status_code, res.get_json()) == (409, self.RETRY)
        assert _ids(admin, unit_id=unit["id"]) == []
        assert _number(make_equipment(cls=cls), cls) == _number(first, cls) + 1

    def test_create_that_cannot_read_back_after_commit_says_reload_and_is_saved(
            self, admin, make_class, make_unit, make_equipment, stale_reread, monkeypatch):
        cls, unit = make_class(), make_unit()
        first = make_equipment(cls=cls)
        reads = []

        def second_read_fails(row):   # the first read is in the transaction, the second after the commit
            reads.append(row)
            return row if len(reads) == 1 else None
        stale_reread(second_read_fails)
        res = admin.post(EQUIPMENT, json={"level": "equipment", "unit_id": unit["id"], "class_id": cls["id"],
                                          "name": "x"})
        monkeypatch.undo()
        assert len(reads) == 2
        assert (res.status_code, res.get_json()) == (409, {"error": equipment.SAVED_BUT_UNREADABLE})
        assert len(_ids(admin, unit_id=unit["id"])) == 1
        assert _number(make_equipment(cls=cls), cls) == _number(first, cls) + 2

    def test_update_that_cannot_read_back_is_409_and_rolls_back(self, admin, make_unit, make_equipment,
                                                                stale_reread, monkeypatch):
        mill, target = make_equipment(), make_unit()
        stale_reread(lambda row: None)
        res = _put(admin, mill, unit_id=target["id"], status="standby")
        monkeypatch.undo()
        assert (res.status_code, res.get_json()) == (409, self.RETRY)
        node = _get(admin, mill)
        assert (node["unit_id"], node["status"]) == (mill["unit_id"], "in_service")
        assert [e[0] for e in _events(admin, mill)] == ["created"]

    def test_a_target_parent_the_snapshot_cannot_see_is_409_parent_id(self, admin, make_class, make_equipment,
                                                                       monkeypatch):
        mill = make_equipment()
        real_read = equipment._read_node
        monkeypatch.setattr(equipment, "_read_node",
                            lambda cur, node_id: None if node_id == mill["id"] else real_read(cur, node_id))
        res = admin.post(EQUIPMENT, json={"level": "component", "parent_id": mill["id"],
                                          "class_id": make_class()["id"], "name": "x"})
        monkeypatch.undo()
        assert (res.status_code, res.get_json()) == (
            409, {"error": "The parent changed while saving — try again", "field": "parent_id"})

    def test_class_and_unit_codes_in_events_come_from_the_locks(self, admin, make_class, make_unit,
                                                                make_equipment, stale_reread, monkeypatch):
        old_cls, new_cls, target = make_class(), make_class(), make_unit()
        mill = make_equipment(cls=old_cls)
        stale_reread(lambda row: {**row, "class_code": "STALE", "unit_code": "STALE"})
        res = _put(admin, mill, class_id=new_cls["id"], unit_id=target["id"])
        monkeypatch.undo()
        assert res.status_code == 200
        assert set(_events(admin, mill)[:2]) == {
            ("class", old_cls["code"], new_cls["code"]),
            ("moved_unit", mill["full_path"], f"{target['full_code']}.{mill['code']}"),
        }

    def test_created_path_takes_the_unit_code_from_the_lock(self, admin, make_unit, make_class,
                                                            stale_reread, monkeypatch):
        unit = make_unit()
        stale_reread(lambda row: {**row, "unit_code": "STALE"})
        res = admin.post(EQUIPMENT, json={"level": "equipment", "unit_id": unit["id"],
                                          "class_id": make_class()["id"], "name": "x"})
        monkeypatch.undo()
        assert res.status_code == 201
        node = _get(admin, res.get_json())
        assert _events(admin, node) == [("created", None, f"{unit['full_code']}.{node['code']}")]


class TestCriticality:

    def test_new_equipment_starts_at_c_and_parts_inherit(self, make_equipment):
        mill = make_equipment()
        part = make_equipment(parent=mill)
        assert (mill["criticality"], mill["effective_criticality"]) == ("C", "C")
        assert (part["criticality"], part["effective_criticality"]) == (None, "C")

    def test_null_on_equipment_is_400(self, admin, make_equipment):
        res = _put(admin, make_equipment(), criticality=None)
        assert (res.status_code, res.get_json()["field"]) == (400, "criticality")

    def test_component_inherits_the_equipments_grade_not_the_component_units(self, admin, make_equipment):
        mill = make_equipment(criticality="A")
        drive = make_equipment(parent=mill, criticality="B")
        motor = make_equipment(parent=drive, level="component")
        assert (drive["effective_criticality"], motor["effective_criticality"]) == ("B", "A")
        grandchild = _get(admin, mill)["children"][0]["children"][0]
        assert (grandchild["criticality"], grandchild["effective_criticality"]) == (None, "A")

    def test_the_filter_uses_the_effective_grade(self, admin, make_unit, make_equipment):
        unit = make_unit()
        mill = make_equipment(unit=unit, criticality="A")
        drive = make_equipment(parent=mill, criticality="B")
        motor = make_equipment(parent=drive, level="component")
        assert set(_ids(admin, unit_id=unit["id"], level="all", criticality="A")) == {mill["id"], motor["id"]}
        assert _ids(admin, unit_id=unit["id"], level="all", criticality="B") == [drive["id"]]


class TestListing:

    @pytest.mark.parametrize("params, field", [
        ({"page": "0"}, "page"), ({"page": "x"}, "page"), ({"per_page": "0"}, "per_page"),
        ({"per_page": "201"}, "per_page"), ({"per_page": "-1"}, "per_page"), ({"unit_id": "a"}, "unit_id"),
        ({"status": "broken"}, "status"), ({"criticality": "D"}, "criticality"), ({"level": "part"}, "level"),
        ({"type_id": "x"}, "type_id"), ({"type_id": "0"}, "type_id"),
        # CR1-02: digits int() rejects, and pages past MAX_PAGE (an OFFSET MariaDB would refuse)
        ({"page": "²"}, "page"), ({"per_page": "²"}, "per_page"), ({"unit_id": "١"}, "unit_id"),
        ({"page": str(api_common.MAX_PAGE + 1)}, "page"), ({"page": "10000000000000000000000000"}, "page"),
    ])
    def test_bad_parameters_are_400(self, admin, params, field):
        res = admin.get(EQUIPMENT, query_string=params)
        assert (res.status_code, res.get_json()["field"]) == (400, field)

    def test_defaults_and_bounds(self, admin):
        body = _list(admin)
        assert (body["page"], body["per_page"]) == (1, 50)
        assert _list(admin, per_page=200)["per_page"] == 200
        assert _list(admin, page=api_common.MAX_PAGE, per_page=200)["items"] == []
        assert admin.get(f"{EQUIPMENT}/").status_code == 200

    def test_paging_ordered_by_code_and_past_the_end(self, admin, make_unit, make_class, make_equipment):
        unit, cls = make_unit(), make_class()
        nodes = [make_equipment(unit=unit, cls=cls) for _ in range(3)]
        page2 = _list(admin, unit_id=unit["id"], per_page=2, page=2)
        assert page2["total"] == 3
        assert [i["id"] for i in page2["items"]] == [nodes[2]["id"]]
        page1 = _list(admin, unit_id=unit["id"], per_page=2)
        assert [i["code"] for i in page1["items"]] == sorted(n["code"] for n in nodes[:2])
        past = _list(admin, unit_id=unit["id"], page=9)
        assert (past["items"], past["total"]) == ([], 3)

    def test_row_fields(self, admin, make_unit, make_equipment):
        unit = make_unit()
        mill = make_equipment(unit=unit)
        item = _list(admin, unit_id=unit["id"])["items"][0]
        # Exact, so it also guards that the list has no notes (S004 § 5.5)
        assert set(item) == {"id", "code", "level", "name", "class_id", "class_code", "type_id", "type_name",
                             "unit_id", "unit", "full_path", "effective_criticality", "status", "part_count"}
        assert (item["unit_id"], item["unit"], item["full_path"]) == (unit["id"], unit["full_code"],
                                                                      mill["full_path"])

    def test_level_filter_default_equipment_and_all(self, admin, make_unit, make_equipment):
        unit = make_unit()
        mill = make_equipment(unit=unit)
        drive = make_equipment(parent=mill)
        motor = make_equipment(parent=drive, level="component")
        assert _ids(admin, unit_id=unit["id"]) == [mill["id"]]
        assert _ids(admin, unit_id=unit["id"], level="component_unit") == [drive["id"]]
        assert _ids(admin, unit_id=unit["id"], level="component") == [motor["id"]]
        assert set(_ids(admin, unit_id=unit["id"], level="all")) == {mill["id"], drive["id"], motor["id"]}

    def test_site_unit_class_and_status_filters(self, admin, make_site, make_unit, make_class, make_equipment):
        site = make_site()
        unit_a, unit_b = make_unit(site), make_unit(site)
        cls = make_class()
        a = make_equipment(unit=unit_a, cls=cls)
        b = make_equipment(unit=unit_b, status="standby")
        assert set(_ids(admin, site_id=site["id"])) == {a["id"], b["id"]}
        assert _ids(admin, unit_id=unit_b["id"]) == [b["id"]]
        assert _ids(admin, class_id=cls["id"]) == [a["id"]]
        assert _ids(admin, site_id=site["id"], status="standby") == [b["id"]]

    def test_search_escapes_wildcards(self, admin, make_unit, make_equipment):
        unit = make_unit()
        pct = make_equipment(unit=unit, name="Fan 50% duty")
        make_equipment(unit=unit, name="Fan 500 duty")
        under = make_equipment(unit=unit, name="Pump A_B")
        make_equipment(unit=unit, name="Pump AxB")
        assert _ids(admin, unit_id=unit["id"], q="0%") == [pct["id"]]
        assert _ids(admin, unit_id=unit["id"], q=" A_B ") == [under["id"]]
        assert len(_ids(admin, unit_id=unit["id"], q="   ")) == 4

    def test_search_matches_code_and_name(self, admin, make_unit, make_equipment):
        unit = make_unit()
        mill = make_equipment(unit=unit, name="Blade mill")
        assert _ids(admin, unit_id=unit["id"], q=mill["code"].lower()) == [mill["id"]]
        assert _ids(admin, unit_id=unit["id"], q="blade") == [mill["id"]]

    def test_scrapped_hidden_unless_requested(self, admin, make_unit, make_equipment):
        unit = make_unit()
        mill = make_equipment(unit=unit)
        _put(admin, mill, status="scrapped")
        assert _ids(admin, unit_id=unit["id"]) == []
        assert _ids(admin, unit_id=unit["id"], include_scrapped=1) == [mill["id"]]

    def test_part_count_is_live_direct_children(self, admin, make_unit, make_equipment):
        unit = make_unit()
        mill = make_equipment(unit=unit)
        drive = make_equipment(parent=mill)
        make_equipment(parent=drive, level="component")   # grandchild: not counted
        dead = make_equipment(parent=mill, level="component")
        _put(admin, dead, status="scrapped")
        assert _list(admin, unit_id=unit["id"])["items"][0]["part_count"] == 1


class TestUnitAccess:

    @pytest.fixture
    def two_units(self, make_unit, make_equipment):
        unit_a, unit_b = make_unit(), make_unit()
        mill_a, mill_b = make_equipment(unit=unit_a), make_equipment(unit=unit_b)
        return unit_a, unit_b, mill_a, mill_b

    def test_engineer_sees_only_their_units(self, user_with_units, two_units, make_equipment):
        unit_a, unit_b, mill_a, mill_b = two_units
        part_a = make_equipment(parent=mill_a)
        engineer = user_with_units("maint_engineer", [unit_a])
        listed = _list(engineer, level="all")
        assert {i["id"] for i in listed["items"]} == {mill_a["id"], part_a["id"]}
        assert listed["total"] == 2
        assert _get(engineer, part_a)["id"] == part_a["id"]
        assert engineer.get(f"{EQUIPMENT}/{mill_b['id']}").status_code == 404

    def test_a_node_elsewhere_is_404_even_with_a_bad_body(self, user_with_units, two_units):
        unit_a, _, _, mill_b = two_units
        engineer = user_with_units("maint_engineer", [unit_a])
        assert _put(engineer, mill_b, name="x").status_code == 404
        assert _put(engineer, mill_b, name="", year="x", code="ZZ").status_code == 404
        assert engineer.put(f"{EQUIPMENT}/{mill_b['id']}", json=[1]).status_code == 404

    def test_targets_outside_their_units_are_403(self, user_with_units, two_units, make_class, make_equipment):
        unit_a, unit_b, mill_a, mill_b = two_units
        engineer = user_with_units("maint_engineer", [unit_a])
        cls = make_class()
        into_b = engineer.post(EQUIPMENT, json={"level": "equipment", "unit_id": unit_b["id"],
                                                "class_id": cls["id"], "name": "x"})
        assert (into_b.status_code, into_b.get_json()["field"]) == (403, "unit_id")
        under_b = engineer.post(EQUIPMENT, json={"level": "component", "parent_id": mill_b["id"],
                                                 "class_id": cls["id"], "name": "x"})
        assert (under_b.status_code, under_b.get_json()["field"]) == (403, "parent_id")
        moved = _put(engineer, mill_a, unit_id=unit_b["id"])
        assert (moved.status_code, moved.get_json()["field"]) == (403, "unit_id")
        part_a = make_equipment(parent=mill_a, level="component")
        reparented = _put(engineer, part_a, parent_id=mill_b["id"])
        assert (reparented.status_code, reparented.get_json()["field"]) == (403, "parent_id")

    def test_a_scrapped_parent_elsewhere_is_403_not_409(self, admin, user_with_units, two_units, make_class):
        """BR3-02: access is refused before the parent's state, so its state is not revealed."""
        unit_a, _, _, mill_b = two_units
        assert _put(admin, mill_b, status="scrapped").status_code == 200
        engineer = user_with_units("maint_engineer", [unit_a])
        res = engineer.post(EQUIPMENT, json={"level": "component", "parent_id": mill_b["id"],
                                             "class_id": make_class()["id"], "name": "x"})
        assert (res.status_code, res.get_json()["field"]) == (403, "parent_id")

    def test_an_inactive_unit_elsewhere_is_409_not_403(self, admin, user_with_units, two_units, make_unit,
                                                       make_class):
        """Decision 4: a unit's state is public (the masters list), so inactive comes before access."""
        unit_a = two_units[0]
        inactive = make_unit()
        assert admin.put(f"{MASTERS}/units/{inactive['id']}", json={"active": False}).status_code == 200
        engineer = user_with_units("maint_engineer", [unit_a])
        res = engineer.post(EQUIPMENT, json={"level": "equipment", "unit_id": inactive["id"],
                                             "class_id": make_class()["id"], "name": "x"})
        assert (res.status_code, res.get_json()["field"]) == (409, "unit_id")

    def test_engineer_writes_inside_their_units(self, user_with_units, two_units, make_class):
        unit_a, _, mill_a, _ = two_units
        engineer = user_with_units("maint_engineer", [unit_a])
        res = engineer.post(EQUIPMENT, json={"level": "component", "parent_id": mill_a["id"],
                                             "class_id": make_class()["id"], "name": "Motor"})
        assert res.status_code == 201
        assert _put(engineer, mill_a, criticality="A").status_code == 200

    def test_a_filter_on_an_inaccessible_unit_is_an_empty_page(self, user_with_units, two_units):
        unit_a, unit_b, _, _ = two_units
        engineer = user_with_units("maint_engineer", [unit_a])
        assert _list(engineer, unit_id=unit_b["id"])["items"] == []
        assert _list(engineer, unit_id=unit_b["id"])["total"] == 0

    @pytest.mark.parametrize("role", ["maint_manager", "it_admin", "admin"])
    def test_senior_roles_see_every_unit(self, user_with_units, two_units, role):
        _, _, mill_a, mill_b = two_units
        client = user_with_units(role, [])
        assert _get(client, mill_b)["id"] == mill_b["id"]
        assert _ids(client, unit_id=mill_a["unit_id"]) == [mill_a["id"]]
        assert _ids(client, unit_id=mill_b["unit_id"]) == [mill_b["id"]]

    def test_a_user_with_no_rows_gets_an_empty_list(self, role_client, uniq, two_units):
        client = role_client("maint_engineer", uniq.username())
        assert _list(client, level="all") == {"items": [], "total": 0, "page": 1, "per_page": 50}

    def test_username_is_compared_lower_case(self, make_person, role_client, uniq, two_units):
        unit_a, _, mill_a, _ = two_units
        username = uniq.username()
        make_person(username=username, sites=[{"site_id": unit_a["site_id"], "role": "maint_technician",
                                               "all_units": False, "unit_ids": [unit_a["id"]]}])
        client = role_client("maint_technician", username.upper())
        assert _get(client, mill_a)["id"] == mill_a["id"]


class TestPermissions:

    @pytest.mark.parametrize("role", ["maint_operator", "maint_technician", "maint_storekeeper"])
    def test_floor_roles_read_and_cannot_write(self, user_with_units, two_units_for_rbac, make_class, role):
        unit, mill = two_units_for_rbac
        client = user_with_units(role, [unit])
        assert _get(client, mill)["id"] == mill["id"]
        assert mill["id"] in _ids(client, unit_id=unit["id"])
        assert _put(client, mill, name="x").status_code == 403
        res = client.post(EQUIPMENT, json={"level": "equipment", "unit_id": unit["id"],
                                           "class_id": make_class()["id"], "name": "x"})
        assert res.status_code == 403

    @pytest.mark.parametrize("role", ["maint_engineer", "maint_manager", "it_admin"])
    def test_writers(self, user_with_units, two_units_for_rbac, make_class, role):
        unit, mill = two_units_for_rbac
        client = user_with_units(role, [unit])
        assert _put(client, mill, name="Edited").status_code == 200
        res = client.post(EQUIPMENT, json={"level": "component", "parent_id": mill["id"],
                                           "class_id": make_class()["id"], "name": "x"})
        assert res.status_code == 201

    def test_unknown_role_is_forbidden(self, role_client):
        assert role_client("nobody").get(EQUIPMENT).status_code == 403


@pytest.fixture
def two_units_for_rbac(make_unit, make_equipment):
    unit = make_unit()
    return unit, make_equipment(unit=unit)


class TestAcceptance:
    """Brief § 9: the firewood mill loaded by an engineer, and a motor moved between breakers."""

    def test_load_the_firewood_mill_and_move_a_motor(self, user_with_units, make_unit, make_class):
        unit = make_unit()
        engineer = user_with_units("maint_engineer", [unit])
        classes = {name: make_class(name=name) for name in ("Blade mill", "Drive", "Motor", "Gearbox", "Breaker")}

        def add(name, cls, **place):
            level = place.pop("level")
            res = engineer.post(EQUIPMENT, json={"level": level, "class_id": classes[cls]["id"], "name": name,
                                                 **place})
            assert res.status_code == 201, res.get_json()
            return res.get_json()

        mill = add("Vertical blade mill", "Blade mill", level="equipment", unit_id=unit["id"])
        drive = add("Mill drive", "Drive", level="component_unit", parent_id=mill["id"])
        add("Drive motor", "Motor", level="component", parent_id=drive["id"])
        add("Drive gearbox", "Gearbox", level="component", parent_id=drive["id"])
        breakers = [add(f"Breaker {i}", "Breaker", level="equipment", unit_id=unit["id"]) for i in (1, 2)]
        motors = [add(f"Breaker {i} motor", "Motor", level="component", parent_id=b["id"])
                  for i, b in enumerate(breakers, start=1)]

        detail = _get(engineer, mill)
        assert [c["id"] for c in detail["children"]] == [drive["id"]]
        assert {c["name"] for c in detail["children"][0]["children"]} == {"Drive motor", "Drive gearbox"}

        res = _put(engineer, motors[0], parent_id=breakers[1]["id"])
        assert res.status_code == 200
        new_path = f"{breakers[1]['full_path']}.{motors[0]['code']}"
        assert res.get_json()["full_path"] == new_path
        assert _events(engineer, motors[0])[0] == ("moved_parent", motors[0]["full_path"], new_path)
        assert {c["id"] for c in _get(engineer, breakers[1])["children"]} == {motors[0]["id"], motors[1]["id"]}


class TestMyUnits:

    def test_a_user_with_two_units_gets_those_ids(self, user_with_units, make_unit):
        unit_a, unit_b = make_unit(), make_unit()
        engineer = user_with_units("maint_engineer", [unit_a, unit_b])
        res = engineer.get(f"{EQUIPMENT}/my-units")
        assert res.status_code == 200
        ids = sorted([unit_a["id"], unit_b["id"]])
        assert res.get_json() == {"all_units": False, "unit_ids": ids, "edit_unit_ids": ids}

    def test_inactive_units_are_left_out(self, admin, user_with_units, make_unit):
        active, inactive = make_unit(), make_unit()
        engineer = user_with_units("maint_engineer", [active, inactive])
        assert admin.put(f"{MASTERS}/units/{inactive['id']}", json={"active": False}).status_code == 200
        assert engineer.get(f"{EQUIPMENT}/my-units").get_json()["unit_ids"] == [active["id"]]

    @pytest.mark.parametrize("role", ["it_admin", "admin"])
    def test_token_roles_get_all_units(self, user_with_units, make_unit, role):
        """S011: only IT admin (token) and admin see every unit; managers see their sites'."""
        client = user_with_units(role, [make_unit()])
        assert client.get(f"{EQUIPMENT}/my-units").get_json() == {"all_units": True, "unit_ids": [],
                                                                   "edit_unit_ids": None}

    def test_a_manager_with_all_units_of_a_site_gets_its_active_units(self, admin, user_at_sites, make_site,
                                                                        make_unit):
        site = make_site()
        unit_a, unit_b, gone = make_unit(site), make_unit(site), make_unit(site)
        admin.put(f"{MASTERS}/units/{gone['id']}", json={"active": False})
        manager, _ = user_at_sites([(site, "maint_manager", "all")])
        body = manager.get(f"{EQUIPMENT}/my-units").get_json()
        assert body["all_units"] is False
        assert body["unit_ids"] == sorted([unit_a["id"], unit_b["id"]]) == body["edit_unit_ids"]

    def test_edit_units_are_where_edit_is_held(self, user_at_sites, make_site, make_unit):
        site_a, site_b = make_site(), make_site()
        unit_a, unit_b = make_unit(site_a), make_unit(site_b)
        client, _ = user_at_sites([(site_a, "maint_engineer", [unit_a]), (site_b, "maint_operator", [unit_b])])
        body = client.get(f"{EQUIPMENT}/my-units").get_json()
        assert body["unit_ids"] == sorted([unit_a["id"], unit_b["id"]])
        assert body["edit_unit_ids"] == [unit_a["id"]]

    def test_a_user_with_no_rows_gets_an_empty_list(self, role_client, uniq):
        client = role_client("maint_engineer", uniq.username())
        assert client.get(f"{EQUIPMENT}/my-units").get_json() == {"all_units": False, "unit_ids": [],
                                                                   "edit_unit_ids": []}

    @pytest.mark.parametrize("role", ["maint_operator", "maint_technician", "maint_engineer", "maint_manager",
                                      "it_admin", "maint_storekeeper"])
    def test_every_role_can_call_it(self, role_client, role):
        assert role_client(role).get(f"{EQUIPMENT}/my-units").status_code == 200


class TestRootCriticality:

    def test_parts_report_the_root_equipments_grade_at_every_depth(self, admin, make_equipment):
        mill = make_equipment(criticality="B")
        drive = make_equipment(parent=mill, criticality="A")
        motor = make_equipment(parent=drive, level="component")
        assert _get(admin, mill)["root_criticality"] == "B"
        assert _get(admin, drive)["root_criticality"] == "B"
        assert _get(admin, motor)["root_criticality"] == "B"

    def test_equipment_reports_its_own_grade(self, admin, make_equipment):
        assert _get(admin, make_equipment(criticality="A"))["root_criticality"] == "A"


class TestTypes:
    """S004 § 5.2: an equipment's type belongs to its class; a class change needs a type decision."""

    def test_create_with_a_type_of_its_class(self, admin, make_class, make_type, make_equipment):
        cls = make_class()
        closed = make_type(cls=cls, name="Closed execution")
        pump = make_equipment(cls=cls, type_id=closed["id"])
        assert (pump["type_id"], pump["type_name"]) == (closed["id"], "Closed execution")
        assert [e[0] for e in _events(admin, pump)] == ["created"]

    def test_create_without_a_type_or_with_null(self, make_equipment):
        assert make_equipment()["type_id"] is None
        node = make_equipment(type_id=None)
        assert (node["type_id"], node["type_name"]) == (None, None)

    def test_a_part_may_have_a_type(self, make_class, make_type, make_equipment):
        cls = make_class()
        squirrel = make_type(cls=cls, name="Squirrel cage")
        motor = make_equipment(parent=make_equipment(), level="component", cls=cls, type_id=squirrel["id"])
        assert motor["type_name"] == "Squirrel cage"

    def test_create_refusals(self, admin, engineer, make_class, make_unit, make_type):
        cls, unit = make_class(), make_unit()
        foreign, retired = make_type(), make_type(cls=cls)
        engineer.put(f"{MASTERS}/equipment-types/{retired['id']}", json={"active": False})
        body = {"level": "equipment", "unit_id": unit["id"], "class_id": cls["id"], "name": "x"}
        for type_id, status, message in (
                (foreign["id"], 400, "This type belongs to another class"),
                (999999, 400, "Unknown type"),
                (retired["id"], 409, "The type is inactive")):
            res = admin.post(EQUIPMENT, json={**body, "type_id": type_id})
            assert (res.status_code, res.get_json()) == (status, {"error": message, "field": "type_id"})
        assert _ids(admin, unit_id=unit["id"]) == []

    def test_put_refusals(self, admin, engineer, make_class, make_type, make_equipment):
        cls = make_class()
        node = make_equipment(cls=cls)
        retired = make_type(cls=cls)
        engineer.put(f"{MASTERS}/equipment-types/{retired['id']}", json={"active": False})
        foreign = _put(admin, node, type_id=make_type()["id"])
        assert (foreign.status_code, foreign.get_json()["field"]) == (400, "type_id")
        assert _put(admin, node, type_id=999999).status_code == 400
        res = _put(admin, node, type_id=retired["id"])
        assert (res.status_code, res.get_json()["error"]) == (409, "The type is inactive")
        assert _get(admin, node)["type_id"] is None

    def test_a_type_deactivated_later_is_kept(self, admin, engineer, make_class, make_type, make_equipment):
        cls = make_class()
        kind = make_type(cls=cls)
        node = make_equipment(cls=cls, type_id=kind["id"])
        engineer.put(f"{MASTERS}/equipment-types/{kind['id']}", json={"active": False})
        # Other fields only, and the type sent back unchanged as the edit dialog does
        assert _put(admin, node, name="Renamed").status_code == 200
        res = _put(admin, node, name="Again", type_id=kind["id"], class_id=cls["id"])
        assert res.status_code == 200
        assert res.get_json()["type_id"] == kind["id"]

    def test_set_change_clear_one_event_each(self, admin, make_class, make_type, make_equipment):
        cls = make_class()
        closed, open_ = make_type(cls=cls, name="Closed execution"), make_type(cls=cls, name="Open execution")
        node = make_equipment(cls=cls)
        for type_id in (closed["id"], open_["id"], None):
            assert _put(admin, node, type_id=type_id).status_code == 200
        assert _events(admin, node)[:3] == [
            ("type", "Open execution", "none"),
            ("type", "Closed execution", "Open execution"),
            ("type", "none", "Closed execution"),
        ]

    def test_class_change_while_typed_needs_a_type_decision(self, admin, make_class, make_type, make_equipment):
        old_cls, new_cls = make_class(), make_class()
        kind = make_type(cls=old_cls, name="Closed execution")
        node = make_equipment(cls=old_cls, type_id=kind["id"])
        res = _put(admin, node, class_id=new_cls["id"])
        assert (res.status_code, res.get_json()) == (
            400, {"error": "Pick a type of the new class, or none", "field": "type_id"})
        assert _get(admin, node)["class_id"] == old_cls["id"]

    def test_class_change_with_no_type(self, admin, make_class, make_type, make_equipment):
        old_cls, new_cls = make_class(), make_class()
        node = make_equipment(cls=old_cls, type_id=make_type(cls=old_cls, name="Closed execution")["id"])
        res = _put(admin, node, class_id=new_cls["id"], type_id=None)
        assert res.status_code == 200
        assert (res.get_json()["class_id"], res.get_json()["type_id"]) == (new_cls["id"], None)
        assert set(_events(admin, node)[:2]) == {
            ("class", old_cls["code"], new_cls["code"]), ("type", "Closed execution", "none")}

    def test_class_change_with_a_type_of_the_new_class(self, admin, make_class, make_type, make_equipment):
        old_cls, new_cls = make_class(), make_class()
        node = make_equipment(cls=old_cls, type_id=make_type(cls=old_cls, name="Closed execution")["id"])
        new_kind = make_type(cls=new_cls, name="Gear")
        res = _put(admin, node, class_id=new_cls["id"], type_id=new_kind["id"])
        assert res.status_code == 200
        assert res.get_json()["type_name"] == "Gear"

    def test_class_change_with_the_old_type_sent_back_is_400(self, admin, make_class, make_type, make_equipment):
        old_cls, new_cls = make_class(), make_class()
        kind = make_type(cls=old_cls)
        node = make_equipment(cls=old_cls, type_id=kind["id"])
        res = _put(admin, node, class_id=new_cls["id"], type_id=kind["id"])
        assert (res.status_code, res.get_json()) == (
            400, {"error": "This type belongs to another class", "field": "type_id"})

    def test_class_change_of_an_untyped_node_needs_nothing(self, admin, make_class, make_equipment):
        node = make_equipment()
        assert _put(admin, node, class_id=make_class()["id"]).status_code == 200

    def test_the_same_type_name_across_a_class_change_is_a_class_event_only(self, admin, make_class, make_type,
                                                                            make_equipment):
        old_cls, new_cls = make_class(), make_class()
        node = make_equipment(cls=old_cls, type_id=make_type(cls=old_cls, name="Standard")["id"])
        res = _put(admin, node, class_id=new_cls["id"], type_id=make_type(cls=new_cls, name="Standard")["id"])
        assert res.status_code == 200
        assert _events(admin, node) == [("class", old_cls["code"], new_cls["code"]),
                                        ("created", None, node["full_path"])]

    def test_the_type_name_in_events_comes_from_the_lock(self, admin, make_class, make_type, make_equipment,
                                                         stale_reread, monkeypatch):
        cls = make_class()
        node = make_equipment(cls=cls)
        kind = make_type(cls=cls, name="Closed execution")
        stale_reread(lambda row: {**row, "type_name": None})
        res = _put(admin, node, type_id=kind["id"])
        monkeypatch.undo()
        assert res.status_code == 200
        assert _events(admin, node)[0] == ("type", "none", "Closed execution")

    def test_the_composite_key_holds_when_the_shell_is_bypassed(self, make_type, make_equipment):
        node = make_equipment()
        with pytest.raises(pymysql.err.IntegrityError):
            _db("UPDATE equipment SET type_id = %s WHERE id = %s", (make_type()["id"], node["id"]))

    def test_a_scrapped_node_takes_no_type_or_notes(self, admin, make_class, make_type, make_equipment):
        cls = make_class()
        node = make_equipment(cls=cls)
        _put(admin, node, status="scrapped")
        assert _put(admin, node, type_id=make_type(cls=cls)["id"]).status_code == 409
        assert _put(admin, node, notes="x").status_code == 409


class TestNotes:

    def test_saved_with_line_breaks_in_the_detail(self, admin, make_equipment):
        node = make_equipment(notes="  Mounted on the left plinth\n\nManual: shelf 3\n")
        assert node["notes"] == "Mounted on the left plinth\n\nManual: shelf 3"
        assert _get(admin, node)["notes"] == node["notes"]

    def test_empty_becomes_null(self, admin, make_equipment):
        node = make_equipment(notes="x")
        assert _put(admin, node, notes="   ").get_json()["notes"] is None

    def test_too_long_is_400(self, admin, make_equipment):
        node = make_equipment()
        assert _put(admin, node, notes="x" * 2000).status_code == 200
        res = _put(admin, node, notes="x" * 2001)
        assert (res.status_code, res.get_json()["field"]) == (400, "notes")

    def test_a_change_writes_no_event_but_the_audit_columns(self, role_client, make_equipment):
        node = make_equipment()
        res = _put(role_client("maint_manager"), node, notes="Bearing grade 6205")
        assert res.status_code == 200
        body = res.get_json()
        assert body["updated_by"] == "test_maint_manager" and body["updated_at"]
        assert [e["event"] for e in body["events"]] == ["created"]


class TestTypeFilterAndSearch:

    def test_type_filter(self, admin, make_unit, make_class, make_type, make_equipment):
        unit, cls = make_unit(), make_class()
        closed, open_ = make_type(cls=cls), make_type(cls=cls)
        a = make_equipment(unit=unit, cls=cls, type_id=closed["id"])
        make_equipment(unit=unit, cls=cls, type_id=open_["id"])
        make_equipment(unit=unit, cls=cls)
        assert _ids(admin, type_id=closed["id"]) == [a["id"]]
        assert _ids(admin, unit_id=unit["id"], class_id=cls["id"], type_id=closed["id"]) == [a["id"]]

    def test_search_finds_a_word_in_the_notes(self, admin, make_unit, make_equipment):
        unit = make_unit()
        node = make_equipment(unit=unit, notes="Spare impeller\nkept in Store B")
        make_equipment(unit=unit, notes="nothing here")
        assert _ids(admin, unit_id=unit["id"], q="IMPELLER") == [node["id"]]

    def test_search_finds_the_type_name(self, admin, make_unit, make_class, make_type, make_equipment):
        unit, cls = make_unit(), make_class()
        closed = make_type(cls=cls, name="Closed execution")
        node = make_equipment(unit=unit, cls=cls, type_id=closed["id"], name="Pump")
        make_equipment(unit=unit, cls=cls, name="Pump")
        assert _ids(admin, unit_id=unit["id"], q="closed") == [node["id"]]
