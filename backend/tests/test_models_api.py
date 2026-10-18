"""Manufacturers and equipment models (S012 § 5.1, § 5.2, § 5.5) — the masters API, against the
test DB.  Needs the dev MariaDB container (tooling/dev/dev-db-up.bat).  Names and designations
come from the ``uniq`` fixture, never fixed values."""

import pymysql
import pytest

import config
from local_db import get_local_db

BASE = "/api/masters"
MAKERS = f"{BASE}/manufacturers"
MODELS = f"{BASE}/equipment-models"


def _db(sql, params=()):
    conn = get_local_db(config.DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()
    finally:
        conn.close()


def _ids(res):
    assert res.status_code == 200, res.get_json()
    return [item["id"] for item in res.get_json()["items"]]


class TestManufacturers:

    def test_create_list_rename(self, engineer, uniq):
        name = uniq.manufacturer_name()
        res = engineer.post(MAKERS, json={"name": f"  {name.replace(' ', '   ')} "})
        assert res.status_code == 201, res.get_json()
        maker = res.get_json()
        assert (maker["name"], maker["active"], maker["created_by"]) == (name, 1, "test_maint_engineer")
        assert maker["id"] in _ids(engineer.get(MAKERS))
        renamed = engineer.put(f"{MAKERS}/{maker['id']}", json={"name": f"{name} Ltd"})
        assert (renamed.status_code, renamed.get_json()["name"]) == (200, f"{name} Ltd")

    def test_duplicate_by_case_or_by_repeated_spaces_is_409(self, engineer, uniq):
        name = f"Atlas Copco {uniq.manufacturer_name()}"
        assert engineer.post(MAKERS, json={"name": name}).status_code == 201
        for twin in (name.upper(), name.replace(" ", "  ")):
            res = engineer.post(MAKERS, json={"name": twin})
            assert (res.status_code, res.get_json()) == (409, {"error": "A manufacturer with this name exists",
                                                               "field": "name"})

    def test_listed_by_name_and_inactive_on_request(self, engineer, make_manufacturer, uniq):
        b = make_manufacturer(name=f"Zb {uniq.manufacturer_name()}")
        a = make_manufacturer(name=f"Za {uniq.manufacturer_name()}")
        listed = _ids(engineer.get(MAKERS))
        assert listed.index(a["id"]) < listed.index(b["id"])
        assert engineer.put(f"{MAKERS}/{a['id']}", json={"active": False}).status_code == 200
        assert a["id"] not in _ids(engineer.get(MAKERS))
        assert a["id"] in _ids(engineer.get(f"{MAKERS}?include_inactive=1"))

    def test_deactivating_one_with_an_active_model_is_409(self, engineer, make_manufacturer, make_model):
        maker = make_manufacturer()
        model = make_model(manufacturer=maker)
        res = engineer.put(f"{MAKERS}/{maker['id']}", json={"active": False})
        assert (res.status_code, res.get_json()["field"]) == (409, "active")
        assert engineer.put(f"{MODELS}/{model['id']}", json={"active": False}).status_code == 200
        assert engineer.put(f"{MAKERS}/{maker['id']}", json={"active": False}).status_code == 200

    def test_unknown_is_404_and_bad_input_400(self, engineer):
        assert engineer.put(f"{MAKERS}/999999", json={"name": "x"}).status_code == 404
        res = engineer.post(MAKERS, json={"name": "x" * 101})
        assert (res.status_code, res.get_json()["field"]) == (400, "name")


class TestModels:

    def test_create_with_a_type_and_list_with_label(self, engineer, make_manufacturer, make_class, make_type,
                                                    uniq):
        maker, cls = make_manufacturer(), make_class(name="Compressor")
        kind = make_type(cls=cls, name="Screw compressor")
        designation = uniq.designation()
        res = engineer.post(MODELS, json={"manufacturer_id": maker["id"], "designation": f" {designation} ",
                                          "class_id": cls["id"], "type_id": kind["id"]})
        assert res.status_code == 201, res.get_json()
        model = res.get_json()
        assert {key: model[key] for key in ("manufacturer_id", "manufacturer_name", "designation", "label",
                                            "class_id", "class_code", "class_name", "type_id", "type_name",
                                            "active")} == {
            "manufacturer_id": maker["id"], "manufacturer_name": maker["name"], "designation": designation,
            "label": f"{maker['name']} {designation}", "class_id": cls["id"], "class_code": cls["code"],
            "class_name": "Compressor", "type_id": kind["id"], "type_name": "Screw compressor", "active": 1}
        assert model["created_by"] == "test_maint_engineer"
        listed = engineer.get(MODELS, query_string={"class_id": cls["id"]}).get_json()
        assert listed == {"items": [model], "total": 1}

    def test_a_model_without_a_type(self, make_model):
        model = make_model()
        assert (model["type_id"], model["type_name"]) == (None, None)

    def test_duplicate_designation_per_maker_by_case_is_409_but_another_maker_is_fine(
            self, engineer, make_manufacturer, make_class, uniq):
        maker, other, cls = make_manufacturer(), make_manufacturer(), make_class()
        designation = f"GA37-{uniq.designation()}"
        body = {"manufacturer_id": maker["id"], "designation": designation, "class_id": cls["id"]}
        assert engineer.post(MODELS, json=body).status_code == 201
        res = engineer.post(MODELS, json={**body, "designation": designation.lower()})
        assert (res.status_code, res.get_json()) == (
            409, {"error": "This manufacturer already has a model with this designation", "field": "designation"})
        assert engineer.post(MODELS, json={**body, "manufacturer_id": other["id"]}).status_code == 201

    @pytest.mark.parametrize("parent", ["manufacturer", "class"])
    def test_an_inactive_manufacturer_or_class_is_409(self, admin, engineer, make_manufacturer, make_class, uniq,
                                                      parent):
        maker, cls = make_manufacturer(), make_class()
        url = f"{MAKERS}/{maker['id']}" if parent == "manufacturer" else f"{BASE}/equipment-classes/{cls['id']}"
        assert admin.put(url, json={"active": False}).status_code == 200
        res = engineer.post(MODELS, json={"manufacturer_id": maker["id"], "designation": uniq.designation(),
                                          "class_id": cls["id"]})
        assert (res.status_code, res.get_json()) == (409, {"error": f"The {parent} is inactive",
                                                           "field": f"{parent}_id"})

    def test_unknown_manufacturer_class_or_type_is_400(self, engineer, make_manufacturer, make_class, uniq):
        maker, cls = make_manufacturer(), make_class()
        body = {"manufacturer_id": maker["id"], "designation": uniq.designation(), "class_id": cls["id"]}
        for field, message in (("manufacturer_id", "Unknown manufacturer"), ("class_id", "Unknown class"),
                               ("type_id", "Unknown type")):
            res = engineer.post(MODELS, json={**body, field: 999999})
            assert (res.status_code, res.get_json()) == (400, {"error": message, "field": field})

    def test_type_of_another_class_is_400_and_an_inactive_type_409(self, engineer, make_manufacturer, make_class,
                                                                    make_type, uniq):
        maker, cls = make_manufacturer(), make_class()
        retired = make_type(cls=cls)
        engineer.put(f"{BASE}/equipment-types/{retired['id']}", json={"active": False})
        body = {"manufacturer_id": maker["id"], "designation": uniq.designation(), "class_id": cls["id"]}
        res = engineer.post(MODELS, json={**body, "type_id": make_type()["id"]})
        assert (res.status_code, res.get_json()) == (400, {"error": "This type belongs to another class",
                                                           "field": "type_id"})
        res = engineer.post(MODELS, json={**body, "type_id": retired["id"]})
        assert (res.status_code, res.get_json()) == (409, {"error": "The type is inactive", "field": "type_id"})

    def test_manufacturer_class_and_type_are_fixed_the_designation_is_not(self, engineer, make_manufacturer,
                                                                          make_class, make_type, make_model,
                                                                          uniq):
        cls = make_class()
        model = make_model(cls=cls)
        for field, value, label in (("manufacturer_id", make_manufacturer()["id"], "Manufacturer"),
                                    ("class_id", make_class()["id"], "Class"),
                                    ("type_id", make_type(cls=cls)["id"], "Type")):
            res = engineer.put(f"{MODELS}/{model['id']}", json={field: value})
            assert (res.status_code, res.get_json()) == (400, {"error": f"{label} cannot be changed", "field": field})
        # Sent back unchanged, as an edit dialog may
        same = {"manufacturer_id": model["manufacturer_id"], "class_id": cls["id"], "type_id": None}
        new_designation = uniq.designation()
        res = engineer.put(f"{MODELS}/{model['id']}", json={**same, "designation": new_designation})
        assert (res.status_code, res.get_json()["designation"]) == (200, new_designation)
        assert res.get_json()["updated_by"] == "test_maint_engineer"

    def test_reactivate_needs_an_active_manufacturer_and_class(self, admin, engineer, make_manufacturer,
                                                               make_class, make_model):
        maker, cls = make_manufacturer(), make_class()
        model = make_model(manufacturer=maker, cls=cls)
        assert engineer.put(f"{MODELS}/{model['id']}", json={"active": False}).status_code == 200
        assert admin.put(f"{MAKERS}/{maker['id']}", json={"active": False}).status_code == 200
        res = engineer.put(f"{MODELS}/{model['id']}", json={"active": True})
        assert (res.status_code, res.get_json()) == (409, {"error": "The manufacturer is inactive",
                                                           "field": "active"})
        admin.put(f"{MAKERS}/{maker['id']}", json={"active": True})
        assert admin.put(f"{BASE}/equipment-classes/{cls['id']}", json={"active": False}).status_code == 200
        res = engineer.put(f"{MODELS}/{model['id']}", json={"active": True})
        assert (res.status_code, res.get_json()) == (409, {"error": "The class is inactive", "field": "active"})
        # Editing the designation of an inactive model is still fine
        assert engineer.put(f"{MODELS}/{model['id']}", json={"designation": "Renamed"}).status_code == 200
        admin.put(f"{BASE}/equipment-classes/{cls['id']}", json={"active": True})
        assert engineer.put(f"{MODELS}/{model['id']}", json={"active": True}).get_json()["active"] == 1

    def test_filters_order_and_inactive(self, engineer, make_manufacturer, make_class, make_model, uniq):
        cls = make_class()
        maker_b = make_manufacturer(name=f"Zb {uniq.manufacturer_name()}")
        maker_a = make_manufacturer(name=f"Za {uniq.manufacturer_name()}")
        b1 = make_model(manufacturer=maker_b, cls=cls, designation="B1")
        a2 = make_model(manufacturer=maker_a, cls=cls, designation="A2")
        a1 = make_model(manufacturer=maker_a, cls=cls, designation="A1")
        other = make_model(manufacturer=maker_a)
        assert _ids(engineer.get(MODELS, query_string={"class_id": cls["id"]})) == [a1["id"], a2["id"], b1["id"]]
        # other's designation is uniq's "M-nnnn", after "A2"
        assert _ids(engineer.get(MODELS, query_string={"manufacturer_id": maker_a["id"]})) == [
            a1["id"], a2["id"], other["id"]]
        engineer.put(f"{MODELS}/{a2['id']}", json={"active": False})
        assert _ids(engineer.get(MODELS, query_string={"class_id": cls["id"]})) == [a1["id"], b1["id"]]
        assert a2["id"] in _ids(engineer.get(MODELS, query_string={"class_id": cls["id"], "include_inactive": "1"}))
        res = engineer.get(MODELS, query_string={"class_id": "x"})
        assert (res.status_code, res.get_json()["field"]) == (400, "class_id")

    def test_unknown_model_is_404(self, engineer):
        assert engineer.put(f"{MODELS}/999999", json={"designation": "x"}).status_code == 404

    def test_a_type_of_another_class_on_a_model_row_is_refused_by_the_database(self, make_model, make_type):
        model = make_model()
        with pytest.raises(pymysql.err.IntegrityError) as caught:
            _db("UPDATE equipment_models SET type_id = %s WHERE id = %s", (make_type()["id"], model["id"]))
        assert caught.value.args[0] == 1452


class TestClassDeactivation:
    """S012 § 5.2: a class with active models can't be deactivated."""

    def test_with_an_active_model_is_409_with_only_inactive_ones_200(self, engineer, make_class, make_model):
        cls = make_class()
        model = make_model(cls=cls)
        res = engineer.put(f"{BASE}/equipment-classes/{cls['id']}", json={"active": False})
        assert (res.status_code, res.get_json()) == (409, {"error": "Deactivate this class's models first",
                                                           "field": "active"})
        assert engineer.put(f"{MODELS}/{model['id']}", json={"active": False}).status_code == 200
        assert engineer.put(f"{BASE}/equipment-classes/{cls['id']}", json={"active": False}).status_code == 200

    def test_renaming_a_class_with_active_models_is_fine(self, engineer, make_class, make_model):
        cls = make_class()
        make_model(cls=cls)
        assert engineer.put(f"{BASE}/equipment-classes/{cls['id']}", json={"name": "Renamed"}).status_code == 200


class TestPermissions:

    def test_an_operator_reads_but_cannot_write(self, role_client, make_manufacturer, make_model, make_class):
        operator = role_client("maint_operator")
        maker, model = make_manufacturer(), make_model()
        assert operator.get(MAKERS).status_code == 200
        assert operator.get(MODELS).status_code == 200
        assert operator.post(MAKERS, json={"name": "x"}).status_code == 403
        assert operator.put(f"{MAKERS}/{maker['id']}", json={"name": "x"}).status_code == 403
        assert operator.post(MODELS, json={"manufacturer_id": maker["id"], "designation": "x",
                                           "class_id": make_class()["id"]}).status_code == 403
        assert operator.put(f"{MODELS}/{model['id']}", json={"designation": "x"}).status_code == 403

    def test_an_engineer_at_one_site_writes(self, user_at_sites, make_site, make_unit, make_class, uniq):
        site = make_site()
        engineer, _ = user_at_sites([(site, "maint_engineer", [make_unit(site)])])
        maker = engineer.post(MAKERS, json={"name": uniq.manufacturer_name()})
        assert maker.status_code == 201
        model = engineer.post(MODELS, json={"manufacturer_id": maker.get_json()["id"], "designation": "GA37",
                                            "class_id": make_class()["id"]})
        assert model.status_code == 201
        assert engineer.put(f"{MODELS}/{model.get_json()['id']}", json={"designation": "GA55"}).status_code == 200
