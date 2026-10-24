"""Meter types (S037 § 5, § 6): the masters API, against the test DB.  Needs the dev MariaDB
container (tooling/dev/dev-db-up.bat).  Names come from the ``uniq`` fixture; the eight seed rows
(migration v29) are read, never changed.
"""

import pytest

PATH = "/api/masters/meter-types"
SEED_NAMES = {"Run hours", "Strokes", "Production count", "Energy", "Odometer", "Oil temperature",
              "Fuel level", "Shift production"}


def _items(res):
    assert res.status_code == 200, res.get_json()
    return res.get_json()["items"]


def _created(res):
    assert res.status_code == 201, res.get_json()
    return res.get_json()


def _refused(res, status, field):
    assert (res.status_code, res.get_json().get("field")) == (status, field), res.get_json()


def _body(uniq, **overrides):
    return {"name": uniq.meter_type_name(), "unit": "bar", "kind": "gauge", "decimals": 1, **overrides}


class TestList:

    def test_the_seed_rows_are_there_and_active(self, engineer):
        by_name = {i["name"]: i for i in _items(engineer.get(PATH))}
        assert SEED_NAMES <= set(by_name)
        assert all(by_name[n]["active"] == 1 for n in SEED_NAMES)
        assert (by_name["Shift production"]["kind"], by_name["Shift production"]["unit"]) == ("amount", "pcs")
        energy = by_name["Energy"]
        assert (energy["kind"], energy["unit"], energy["decimals"], energy["expected_answer"]) == (
            "counter", "kWh", 1, None)
        assert by_name["Oil temperature"]["unit"] == "°C"
        assert by_name["Run hours"]["created_by"] == "migration-v29"

    def test_the_list_has_a_total_and_is_by_name(self, engineer):
        res = engineer.get(PATH)
        names = [i["name"] for i in _items(res)]
        assert names == sorted(names, key=str.lower) and res.get_json()["total"] == len(names)

    def test_inactive_rows_only_with_include_inactive(self, engineer, uniq):
        row = _created(engineer.post(PATH, json=_body(uniq)))
        engineer.put(f"{PATH}/{row['id']}", json={"active": False})
        assert row["id"] not in [i["id"] for i in _items(engineer.get(PATH))]
        assert row["id"] in [i["id"] for i in _items(engineer.get(f"{PATH}?include_inactive=1"))]


class TestWhoMayEdit:

    @pytest.mark.parametrize("role", ["maint_engineer", "it_admin"])
    def test_engineer_and_it_admin_create(self, role_client, uniq, role):
        row = _created(role_client(role).post(PATH, json=_body(uniq)))
        assert (row["active"], row["created_by"], row["kind"]) == (1, f"test_{role}", "gauge")

    @pytest.mark.parametrize("role", ["maint_operator", "maint_storekeeper"])
    def test_others_read_but_may_not_write(self, role_client, engineer, uniq, role):
        row = _created(engineer.post(PATH, json=_body(uniq)))
        client = role_client(role)
        assert row["id"] in [i["id"] for i in _items(client.get(PATH))]
        assert client.post(PATH, json=_body(uniq)).status_code == 403
        assert client.put(f"{PATH}/{row['id']}", json={"active": False}).status_code == 403


class TestCreateAndEdit:

    def test_decimals_default_to_zero(self, engineer, uniq):
        row = _created(engineer.post(PATH, json={"name": uniq.meter_type_name(), "unit": "mm", "kind": "gauge"}))
        assert (row["decimals"], row["expected_answer"]) == (0, None)

    def test_update_kind_unit_decimals_then_deactivate_and_reactivate(self, engineer, uniq):
        row = _created(engineer.post(PATH, json=_body(uniq)))
        res = engineer.put(f"{PATH}/{row['id']}", json={"kind": "counter", "unit": " kWh ", "decimals": 2})
        assert res.status_code == 200, res.get_json()
        edited = res.get_json()
        assert (edited["kind"], edited["unit"], edited["decimals"], edited["updated_by"]) == (
            "counter", "kWh", 2, "test_maint_engineer")
        assert engineer.put(f"{PATH}/{row['id']}", json={"active": False}).get_json()["active"] == 0
        assert engineer.put(f"{PATH}/{row['id']}", json={"active": True}).get_json()["active"] == 1

    def test_a_yes_no_type_is_created_without_a_unit_and_read_back(self, engineer, uniq):
        row = _created(engineer.post(PATH, json={
            "name": uniq.meter_type_name(), "kind": "yes_no", "expected_answer": "yes"}))
        assert (row["unit"], row["expected_answer"], row["decimals"]) == (None, "yes", 0)
        listed = {i["id"]: i for i in _items(engineer.get(PATH))}[row["id"]]
        assert listed == row

    def test_the_panels_five_fields_for_a_yes_no_type(self, engineer, uniq):
        row = _created(engineer.post(PATH, json={
            "name": uniq.meter_type_name(), "kind": "yes_no", "unit": None, "expected_answer": "no", "decimals": 0}))
        assert row["expected_answer"] == "no"

    def test_a_put_from_gauge_to_yes_no_needs_the_whole_shape(self, engineer, uniq):
        row = _created(engineer.post(PATH, json=_body(uniq)))
        _refused(engineer.put(f"{PATH}/{row['id']}", json={"kind": "yes_no", "expected_answer": "yes"}), 400, "unit")
        ok = engineer.put(f"{PATH}/{row['id']}", json={
            "kind": "yes_no", "unit": None, "expected_answer": "yes", "decimals": 0})
        assert ok.status_code == 200, ok.get_json()
        assert (ok.get_json()["unit"], ok.get_json()["expected_answer"]) == (None, "yes")

    def test_a_put_from_yes_no_to_gauge_clears_the_answer(self, engineer, uniq):
        row = _created(engineer.post(PATH, json={
            "name": uniq.meter_type_name(), "kind": "yes_no", "expected_answer": "yes"}))
        res = engineer.put(f"{PATH}/{row['id']}", json={
            "kind": "gauge", "unit": "mm", "expected_answer": None, "decimals": 1})
        assert res.status_code == 200, res.get_json()
        assert (res.get_json()["expected_answer"], res.get_json()["unit"]) == (None, "mm")

    def test_deactivating_does_not_trip_over_the_stored_shape(self, engineer, uniq):
        row = _created(engineer.post(PATH, json={
            "name": uniq.meter_type_name(), "kind": "yes_no", "expected_answer": "yes"}))
        assert engineer.put(f"{PATH}/{row['id']}", json={"active": False}).status_code == 200

    @pytest.mark.parametrize("body, field", [
        ({"unit": ""}, "unit"),
        ({"kind": "dial"}, "kind"),
        ({"decimals": 4}, "decimals"),
        ({"decimals": True}, "decimals"),
        ({"name": "  "}, "name"),
        ({"expected_answer": "yes"}, "expected_answer"),
    ])
    def test_refusals_name_the_field(self, engineer, uniq, body, field):
        _refused(engineer.post(PATH, json=_body(uniq, **body)), 400, field)

    def test_unknown_id_is_404(self, engineer):
        assert engineer.put(f"{PATH}/999999", json={"active": False}).status_code == 404


class TestDuplicates:

    def test_a_duplicate_name_in_another_case_is_409(self, engineer, uniq):
        row = _created(engineer.post(PATH, json=_body(uniq)))
        _refused(engineer.post(PATH, json=_body(uniq, name=row["name"].upper())), 409, "name")

    def test_a_seed_name_is_taken(self, engineer, uniq):
        _refused(engineer.post(PATH, json=_body(uniq, name="run hours")), 409, "name")

    def test_renaming_to_a_taken_name_is_409(self, engineer, uniq):
        first = _created(engineer.post(PATH, json=_body(uniq)))
        second = _created(engineer.post(PATH, json=_body(uniq)))
        _refused(engineer.put(f"{PATH}/{second['id']}", json={"name": first["name"]}), 409, "name")


class TestFrozenOnceUsed:
    """S038 § 1.5: kind, unit, decimals and the expected answer freeze once a model meter or a
    node meter uses the type, active or not; name and active stay editable."""

    IN_USE = ("This meter type is in use. Its kind, unit, decimals and expected answer cannot change. "
              "Make a new meter type.")

    def _on_a_model(self, engineer, make_model, meter_type):
        res = engineer.post(f"/api/masters/equipment-models/{make_model()['id']}/meters",
                            json={"meter_type_id": meter_type["id"]})
        assert res.status_code == 201, res.get_json()
        return res.get_json()

    @pytest.mark.parametrize("change, field", [
        ({"kind": "counter"}, "kind"), ({"unit": "bar"}, "unit"), ({"decimals": 2}, "decimals"),
    ])
    def test_a_change_on_a_type_a_model_uses_is_409(self, engineer, make_model, make_meter_type, change, field):
        meter_type = make_meter_type()
        self._on_a_model(engineer, make_model, meter_type)
        res = engineer.put(f"{PATH}/{meter_type['id']}", json=change)
        assert (res.status_code, res.get_json()) == (409, {"error": self.IN_USE, "field": field})

    def test_the_freeze_holds_with_an_inactive_link(self, engineer, make_model, make_meter_type):
        meter_type = make_meter_type()
        row = self._on_a_model(engineer, make_model, meter_type)
        engineer.put(f"/api/masters/model-meters/{row['id']}", json={"active": False})
        assert engineer.put(f"{PATH}/{meter_type['id']}", json={"unit": "bar"}).status_code == 409

    def test_a_node_meter_freezes_the_type_too(self, engineer, admin, make_equipment, make_meter_type):
        meter_type = make_meter_type()
        node = make_equipment()
        assert admin.post(f"/api/equipment/{node['id']}/meters",
                             json={"meter_type_id": meter_type["id"]}).status_code == 201
        assert engineer.put(f"{PATH}/{meter_type['id']}", json={"decimals": 0}).status_code == 409

    def test_a_yes_no_type_s_expected_answer_freezes(self, engineer, make_model, make_meter_type):
        meter_type = make_meter_type(kind="yes_no", expected_answer="yes")
        self._on_a_model(engineer, make_model, meter_type)
        res = engineer.put(f"{PATH}/{meter_type['id']}", json={"expected_answer": "no"})
        assert (res.status_code, res.get_json()["field"]) == (409, "expected_answer")

    def test_name_and_active_stay_editable_and_the_same_values_pass(self, engineer, uniq, make_model,
                                                                    make_meter_type):
        meter_type = make_meter_type()
        self._on_a_model(engineer, make_model, meter_type)
        same = {"name": uniq.meter_type_name(), "unit": "°C", "kind": "gauge", "decimals": 1, "expected_answer": None}
        res = engineer.put(f"{PATH}/{meter_type['id']}", json=same)
        assert res.status_code == 200, res.get_json()
        assert engineer.put(f"{PATH}/{meter_type['id']}", json={"active": False}).status_code == 200

    def test_an_unused_type_still_changes(self, engineer, make_meter_type):
        meter_type = make_meter_type()
        assert engineer.put(f"{PATH}/{meter_type['id']}", json={"unit": "bar", "decimals": 2}).status_code == 200
