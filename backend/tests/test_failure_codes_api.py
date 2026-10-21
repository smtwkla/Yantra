"""Failure codes (S016 § 5, § 6): failure modes, causes and maintenance actions — the masters
API, against the test DB.  Needs the dev MariaDB container (tooling/dev/dev-db-up.bat).  Codes
and labels come from the ``uniq`` fixture; the seed rows (migration v11) are read, never changed.
"""

import pytest

BASE = "/api/masters"
MODES = f"{BASE}/failure-modes"
CAUSES = f"{BASE}/failure-causes"
ACTIONS = f"{BASE}/maintenance-actions"
CLASSES = f"{BASE}/equipment-classes"


def _items(res):
    assert res.status_code == 200, res.get_json()
    return res.get_json()["items"]


def _ids(res):
    return [item["id"] for item in _items(res)]


def _created(res):
    assert res.status_code == 201, res.get_json()
    return res.get_json()


def _refused(res, status, field):
    assert (res.status_code, res.get_json().get("field")) == (status, field), res.get_json()


def _body(path, uniq):
    body = {"code": uniq.failure_code(), "label": uniq.failure_label()}
    if path == CAUSES:
        body["cause_group"] = "operation"
    return body


# Each list's create / edit / deactivate / reactivate, by each editor
_LISTS = [MODES, CAUSES, ACTIONS]


class TestWhoMayEdit:

    @pytest.mark.parametrize("path", _LISTS)
    @pytest.mark.parametrize("role", ["maint_engineer", "maint_manager", "it_admin"])
    def test_editor_creates_edits_deactivates_reactivates(self, role_client, uniq, path, role):
        client = role_client(role)
        row = _created(client.post(path, json={**_body(path, uniq), "description": "  Help text "}))
        assert (row["active"], row["description"], row["created_by"]) == (1, "Help text", f"test_{role}")
        new_label = uniq.failure_label()
        edited = client.put(f"{path}/{row['id']}", json={"label": new_label, "description": ""})
        assert edited.status_code == 200, edited.get_json()
        assert (edited.get_json()["label"], edited.get_json()["description"]) == (new_label, None)
        assert edited.get_json()["updated_by"] == f"test_{role}"
        assert client.put(f"{path}/{row['id']}", json={"active": False}).get_json()["active"] == 0
        assert row["id"] not in _ids(client.get(path))
        assert row["id"] in _ids(client.get(f"{path}?include_inactive=1"))
        assert client.put(f"{path}/{row['id']}", json={"active": True}).get_json()["active"] == 1
        assert row["id"] in _ids(client.get(path))

    @pytest.mark.parametrize("path", _LISTS)
    @pytest.mark.parametrize("role", ["maint_operator", "maint_technician", "maint_supervisor", "maint_storekeeper"])
    def test_others_read_but_may_not_write(self, role_client, engineer, uniq, path, role):
        row = _created(engineer.post(path, json=_body(path, uniq)))
        client = role_client(role)
        assert row["id"] in _ids(client.get(path))
        assert client.post(path, json=_body(path, uniq)).status_code == 403
        assert client.put(f"{path}/{row['id']}", json={"active": False}).status_code == 403

    @pytest.mark.parametrize("path", _LISTS)
    def test_unknown_id_is_404(self, engineer, path):
        assert engineer.put(f"{path}/999999", json={"label": "x"}).status_code == 404


class TestDuplicates:

    @pytest.mark.parametrize("path", _LISTS)
    def test_duplicate_code_is_409(self, engineer, uniq, path):
        first = _created(engineer.post(path, json=_body(path, uniq)))
        res = engineer.post(path, json={**_body(path, uniq), "code": first["code"].lower()})
        _refused(res, 409, "code")
        other = _created(engineer.post(path, json=_body(path, uniq)))
        _refused(engineer.put(f"{path}/{other['id']}", json={"code": first["code"]}), 409, "code")

    @pytest.mark.parametrize("path", [CAUSES, ACTIONS])
    def test_duplicate_label_is_409_whatever_the_case(self, engineer, uniq, path):
        first = _created(engineer.post(path, json=_body(path, uniq)))
        res = engineer.post(path, json={**_body(path, uniq), "label": f" {first['label'].upper()} "})
        _refused(res, 409, "label")

    def test_seed_codes_are_taken(self, engineer, uniq):
        _refused(engineer.post(MODES, json={"code": "noi", "label": uniq.failure_label()}), 409, "code")
        _refused(engineer.post(CAUSES, json={"code": "3.4", "label": uniq.failure_label(), "cause_group": "misc"}),
                 409, "code")
        _refused(engineer.post(ACTIONS, json={"code": "12", "label": uniq.failure_label()}), 409, "code")

    @pytest.mark.parametrize("path", _LISTS)
    def test_bad_input_is_400(self, engineer, uniq, path):
        _refused(engineer.post(path, json={**_body(path, uniq), "code": "1..2"}), 400, "code")
        _refused(engineer.post(path, json={**_body(path, uniq), "label": "x" * 61}), 400, "label")


class TestModeClass:

    def test_class_filter_gives_the_class_and_general(self, engineer, make_class, make_mode):
        press, pump = make_class(), make_class()
        general, of_press, of_pump = make_mode(), make_mode(cls=press), make_mode(cls=pump)
        listed = _items(engineer.get(f"{MODES}?class_id={press['id']}"))
        ids = [m["id"] for m in listed]
        assert general["id"] in ids and of_press["id"] in ids and of_pump["id"] not in ids
        assert [m["label"] for m in listed] == sorted((m["label"] for m in listed), key=str.lower)
        assert {m["class_code"] for m in listed} == {None, press["code"]}
        assert "NOI" in {m["code"] for m in listed}   # the seed modes are General

    def test_list_without_filter_is_general_first(self, engineer, make_class, make_mode):
        of_class, general = make_mode(cls=make_class()), make_mode()
        listed = _items(engineer.get(MODES))
        ids = [m["id"] for m in listed]
        assert ids.index(general["id"]) < ids.index(of_class["id"])
        flags = [m["class_id"] is not None for m in listed]
        assert flags == sorted(flags)

    def test_include_inactive_with_the_class_filter(self, engineer, make_class, make_mode):
        cls = make_class()
        mode = make_mode(cls=cls)
        assert engineer.put(f"{MODES}/{mode['id']}", json={"active": False}).status_code == 200
        assert mode["id"] not in _ids(engineer.get(f"{MODES}?class_id={cls['id']}"))
        assert mode["id"] in _ids(engineer.get(f"{MODES}?class_id={cls['id']}&include_inactive=1"))

    def test_unknown_class_filter_gives_the_general_modes(self, engineer, make_mode):
        # Report decision 7: not refused; S017 passes a real equipment's class.
        general = make_mode()
        listed = _items(engineer.get(f"{MODES}?class_id=999999"))
        assert general["id"] in [m["id"] for m in listed]
        assert {m["class_id"] for m in listed} == {None}

    def test_inactive_class_filter_gives_general_and_its_own_modes(self, engineer, make_class, make_mode):
        cls = make_class()
        general, own = make_mode(), make_mode(cls=cls)
        assert engineer.put(f"{CLASSES}/{cls['id']}", json={"active": False}).status_code == 200
        ids = _ids(engineer.get(f"{MODES}?class_id={cls['id']}"))
        assert general["id"] in ids and own["id"] in ids

    def test_bad_class_filter_is_400(self, engineer):
        _refused(engineer.get(f"{MODES}?class_id=x"), 400, "class_id")

    def test_class_is_fixed_after_create(self, engineer, make_class, make_mode):
        cls = make_class()
        mode = make_mode(cls=cls)
        _refused(engineer.put(f"{MODES}/{mode['id']}", json={"class_id": make_class()["id"]}), 400, "class_id")
        _refused(engineer.put(f"{MODES}/{mode['id']}", json={"class_id": None}), 400, "class_id")
        same = engineer.put(f"{MODES}/{mode['id']}", json={"class_id": cls["id"], "description": "x"})
        assert (same.status_code, same.get_json()["class_id"]) == (200, cls["id"])
        general = make_mode()
        _refused(engineer.put(f"{MODES}/{general['id']}", json={"class_id": cls["id"]}), 400, "class_id")

    def test_unknown_class_is_400(self, engineer, uniq):
        res = engineer.post(MODES, json={"code": uniq.failure_code(), "label": uniq.failure_label(),
                                         "class_id": 999999})
        assert (res.status_code, res.get_json()) == (400, {"error": "Unknown class", "field": "class_id"})

    def test_inactive_class_at_create_and_at_reactivation_is_409(self, engineer, make_class, make_mode, uniq):
        cls = make_class()
        mode = make_mode(cls=cls)
        assert engineer.put(f"{MODES}/{mode['id']}", json={"active": False}).status_code == 200
        # A class's modes don't stop it being deactivated (S016 § 5.2)
        assert engineer.put(f"{CLASSES}/{cls['id']}", json={"active": False}).status_code == 200
        _refused(engineer.post(MODES, json={"code": uniq.failure_code(), "label": uniq.failure_label(),
                                            "class_id": cls["id"]}), 409, "class_id")
        _refused(engineer.put(f"{MODES}/{mode['id']}", json={"active": True}), 409, "active")
        # Other edits of a mode of an inactive class still go through
        assert engineer.put(f"{MODES}/{mode['id']}", json={"description": "x"}).status_code == 200
        assert engineer.put(f"{CLASSES}/{cls['id']}", json={"active": True}).status_code == 200
        assert engineer.put(f"{MODES}/{mode['id']}", json={"active": True}).status_code == 200

    def test_general_mode_reactivates_without_a_class(self, engineer, make_mode):
        mode = make_mode()
        assert engineer.put(f"{MODES}/{mode['id']}", json={"active": False}).status_code == 200
        assert engineer.put(f"{MODES}/{mode['id']}", json={"active": True}).status_code == 200


class TestModeLabels:

    def test_same_label_in_the_same_class_is_409(self, engineer, make_class, make_mode, uniq):
        cls = make_class()
        mode = make_mode(cls=cls)
        _refused(engineer.post(MODES, json={"code": uniq.failure_code(), "label": mode["label"].lower(),
                                            "class_id": cls["id"]}), 409, "label")

    def test_class_label_equal_to_a_general_one_is_409(self, engineer, make_class, uniq):
        res = engineer.post(MODES, json={"code": uniq.failure_code(), "label": "abnormal  NOISE",
                                         "class_id": make_class()["id"]})
        _refused(res, 409, "label")
        assert "NOI" in res.get_json()["error"]

    def test_general_label_equal_to_any_class_mode_is_409(self, engineer, make_class, make_mode, uniq):
        mode = make_mode(cls=make_class())
        _refused(engineer.post(MODES, json={"code": uniq.failure_code(), "label": mode["label"]}), 409, "label")

    def test_same_label_in_two_classes_is_allowed(self, make_class, make_mode, uniq):
        label = uniq.failure_label()
        make_mode(cls=make_class(), label=label)
        make_mode(cls=make_class(), label=label)

    def test_inactive_modes_count(self, engineer, make_class, make_mode, uniq):
        mode = make_mode(cls=make_class())
        assert engineer.put(f"{MODES}/{mode['id']}", json={"active": False}).status_code == 200
        res = engineer.post(MODES, json={"code": uniq.failure_code(), "label": mode["label"]})
        _refused(res, 409, "label")

    def test_rename_into_a_clash_is_409_and_to_itself_is_fine(self, engineer, make_class, make_mode):
        cls = make_class()
        first, second = make_mode(cls=cls), make_mode(cls=cls)
        _refused(engineer.put(f"{MODES}/{second['id']}", json={"label": first["label"]}), 409, "label")
        same = engineer.put(f"{MODES}/{first['id']}", json={"label": first["label"].upper()})
        assert (same.status_code, same.get_json()["label"]) == (200, first["label"].upper())


class TestOrder:

    def test_causes_by_group_then_code(self, engineer, uniq):
        local = _created(engineer.post(CAUSES, json={"code": "Z9", "label": uniq.failure_label(),
                                                     "cause_group": "design"}))
        listed = _items(engineer.get(CAUSES))
        codes = [c["code"] for c in listed]
        # The local design cause sits in the design group, before every fabrication cause
        assert codes.index("1.2") < codes.index(local["code"]) < codes.index("2.1")
        groups = [c["cause_group"] for c in listed]
        order = ["design", "fabrication", "operation", "management", "misc"]
        assert [order.index(g) for g in groups] == sorted(order.index(g) for g in groups)

    def test_cause_group_may_change(self, engineer, uniq):
        cause = _created(engineer.post(CAUSES, json=_body(CAUSES, uniq)))
        res = engineer.put(f"{CAUSES}/{cause['id']}", json={"cause_group": "management"})
        assert (res.status_code, res.get_json()["cause_group"]) == (200, "management")
        _refused(engineer.put(f"{CAUSES}/{cause['id']}", json={"cause_group": "other"}), 400, "cause_group")

    def test_actions_in_number_order(self, engineer):
        seeds = [a["code"] for a in _items(engineer.get(ACTIONS)) if a["created_by"] == "migration-v11"]
        assert seeds == [str(n) for n in range(1, 13)]


class TestModeCodeFrozenOnceUsed:
    """S017 § 5.7: once a ticket uses a mode, its code can no longer change; the label,
    description and active flag stay editable."""

    def test_a_used_modes_code_is_409_and_its_label_still_changes(self, engineer, make_equipment, make_mode,
                                                                    make_ticket, uniq):
        machine = make_equipment()
        mode = make_mode()
        make_ticket(machine, failure_mode_id=mode["id"])
        res = engineer.put(f"{MODES}/{mode['id']}", json={"code": uniq.failure_code()})
        _refused(res, 409, "code")
        assert res.get_json()["error"] == "This code is used by tickets and can no longer change"
        same = engineer.put(f"{MODES}/{mode['id']}", json={"code": mode["code"], "label": uniq.failure_label(),
                                                         "description": "Plain words"})
        assert same.status_code == 200, same.get_json()
        assert engineer.put(f"{MODES}/{mode['id']}", json={"active": False}).status_code == 200

    def test_an_unused_modes_code_still_changes(self, engineer, make_mode, uniq):
        mode = make_mode()
        code = uniq.failure_code()
        res = engineer.put(f"{MODES}/{mode['id']}", json={"code": code})
        assert (res.status_code, res.get_json()["code"]) == (200, code)


class TestCauseAndActionCodeFrozenOnceUsed:
    """S018 § 5.6: as modes — a cause or action used by a ticket keeps its code; label, group,
    description and active stay editable; a re-save with the code unchanged is accepted."""

    @pytest.mark.parametrize("path, column", [(CAUSES, "cause_id"), (ACTIONS, "action_id")])
    def test_a_used_codes_code_is_409_and_the_rest_still_changes(self, engineer, make_equipment, make_ticket,
                                                                  db_rows, uniq, path, column):
        record = _created(engineer.post(path, json=_body(path, uniq)))
        ticket = make_ticket(make_equipment())
        db_rows(f"UPDATE tickets SET {column} = %s WHERE id = %s", (record["id"], ticket["id"]))
        res = engineer.put(f"{path}/{record['id']}", json={"code": uniq.failure_code()})
        _refused(res, 409, "code")
        assert res.get_json()["error"] == "This code is used by tickets and can no longer change"
        changes = {"code": record["code"], "label": uniq.failure_label()}
        if path == CAUSES:
            changes["cause_group"] = "management"
        same = engineer.put(f"{path}/{record['id']}", json=changes)
        assert same.status_code == 200, same.get_json()
        assert engineer.put(f"{path}/{record['id']}", json={"active": False}).status_code == 200

    @pytest.mark.parametrize("path", [CAUSES, ACTIONS])
    def test_an_unused_codes_code_still_changes(self, engineer, uniq, path):
        record = _created(engineer.post(path, json=_body(path, uniq)))
        code = uniq.failure_code()
        res = engineer.put(f"{path}/{record['id']}", json={"code": code})
        assert (res.status_code, res.get_json()["code"]) == (200, code)
