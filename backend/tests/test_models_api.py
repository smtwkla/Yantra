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


# ---------------------------------------------------------------------------
# Model meters (S038 § 5.3, § 6)
# ---------------------------------------------------------------------------

MODEL_METERS = f"{BASE}/model-meters"


def _meters_url(model):
    return f"{MODELS}/{model['id']}/meters"


def _add(client, model, meter_type, **limits):
    return client.post(_meters_url(model), json={"meter_type_id": meter_type["id"], **limits})


def _refusal(res):
    body = res.get_json()
    return res.status_code, body.get("field"), body["error"]


class TestModelMeters:

    def test_add_with_limits_then_list(self, engineer, make_model, make_meter_type):
        model, oil = make_model(), make_meter_type()
        res = _add(engineer, model, oil, min_value="10", max_value=60)
        assert res.status_code == 201, res.get_json()
        row = res.get_json()
        assert (row["min_value"], row["max_value"], row["limits_text"], row["active"]) == (
            "10", "60", "Limits: 10–60 °C", 1)
        assert row["meter_type"] == {"id": oil["id"], "name": oil["name"], "unit": "°C", "kind": "gauge",
                                     "decimals": 1, "expected_answer": None}
        listed = engineer.get(_meters_url(model))
        assert listed.status_code == 200 and listed.get_json() == [row]

    def test_the_list_is_by_name_and_a_non_gauge_has_no_limits_text(self, engineer, make_model, make_meter_type):
        model = make_model()
        types = [make_meter_type(kind="yes_no", expected_answer="no"), make_meter_type(kind="counter", unit="h")]
        for meter_type in types:
            assert _add(engineer, model, meter_type).status_code == 201
        rows = engineer.get(_meters_url(model)).get_json()
        assert [r["meter_type"]["name"] for r in rows] == sorted(t["name"] for t in types)
        assert {r["limits_text"] for r in rows} == {None}
        assert {r["meter_type"]["expected_answer"] for r in rows} == {"no", None}

    def test_set_limits_one_side_keeps_the_other(self, engineer, make_model, make_meter_type):
        model = make_model()
        row = _add(engineer, model, make_meter_type(), min_value="10", max_value="60").get_json()
        res = engineer.put(f"{MODEL_METERS}/{row['id']}", json={"max_value": "55.5"})
        assert res.status_code == 200, res.get_json()
        assert (res.get_json()["min_value"], res.get_json()["max_value"]) == ("10", "55.5")
        res = engineer.put(f"{MODEL_METERS}/{row['id']}", json={"min_value": None})
        assert res.get_json()["limits_text"] == "Limits: up to 55.5 °C"
        engineer.put(f"{MODEL_METERS}/{row['id']}", json={"min_value": "10"})
        assert _refusal(engineer.put(f"{MODEL_METERS}/{row['id']}", json={"min_value": "60"})) == (
            400, "max_value", "Min must not be above Max")

    def test_remove_then_add_again_reactivates_the_row_with_the_sent_limits(self, engineer, make_model,
                                                                             make_meter_type):
        model, oil = make_model(), make_meter_type()
        row = _add(engineer, model, oil, min_value="10", max_value="60").get_json()
        res = engineer.put(f"{MODEL_METERS}/{row['id']}", json={"active": False})
        assert res.status_code == 200 and res.get_json()["active"] == 0
        assert engineer.get(_meters_url(model)).get_json() == []
        assert [r["id"] for r in engineer.get(f"{_meters_url(model)}?include_inactive=1").get_json()] == [row["id"]]
        # A removed row is not changed by PUT; an add brings it back
        assert engineer.put(f"{MODEL_METERS}/{row['id']}", json={"max_value": "5"}).status_code == 404
        back = _add(engineer, model, oil, max_value="70")
        assert back.status_code == 201
        assert (back.get_json()["id"], back.get_json()["min_value"], back.get_json()["max_value"],
                back.get_json()["active"]) == (row["id"], None, "70", 1)

    def test_a_put_cannot_reactivate_or_use_the_model_s_limits(self, engineer, make_model, make_meter_type):
        row = _add(engineer, make_model(), make_meter_type()).get_json()
        assert _refusal(engineer.put(f"{MODEL_METERS}/{row['id']}", json={"active": True}))[:2] == (400, "active")
        assert engineer.put(f"{MODEL_METERS}/{row['id']}", json={"use_model_limits": True}).status_code == 400

    @pytest.mark.parametrize("kind, message", [
        ("counter", "A counter has no limits"),
        ("amount", "An amount per period has no limits"),
        ("yes_no", "A Yes / No meter has no limits"),
    ])
    def test_limits_on_a_non_gauge_are_refused(self, engineer, make_model, make_meter_type, kind, message):
        meter_type = make_meter_type(kind=kind, unit="pcs")
        assert _refusal(_add(engineer, make_model(), meter_type, max_value="5")) == (400, "max_value", message)
        # explicit nulls pass (a form that posts every field)
        assert _add(engineer, make_model(), meter_type, min_value=None, max_value=None).status_code == 201

    def test_a_number_with_too_many_decimals_is_refused(self, engineer, make_model, make_meter_type):
        assert _refusal(_add(engineer, make_model(), make_meter_type(), max_value="62.55")) == (
            400, "max_value", "Enter a number with up to 1 decimal")
        assert _refusal(_add(engineer, make_model(), make_meter_type(decimals=0), max_value=62.0)) == (
            400, "max_value", "Enter a whole number")

    def test_refusals(self, engineer, admin, make_model, make_meter_type):
        model, oil = make_model(), make_meter_type()
        assert _refusal(engineer.post(_meters_url(model), json={})) == (400, "meter_type_id", "Pick a meter type")
        assert _refusal(engineer.post(_meters_url(model), json={"meter_type_id": 99999999}))[:2] == (
            400, "meter_type_id")
        assert _add(engineer, model, oil).status_code == 201
        assert _refusal(_add(engineer, model, oil)) == (409, "meter_type_id", "This model already has this meter")
        inactive = make_meter_type()
        admin.put(f"{BASE}/meter-types/{inactive['id']}", json={"active": False})
        assert _refusal(_add(engineer, model, inactive)) == (409, "meter_type_id", "This meter type is inactive. Pick another meter type.")
        assert engineer.post(f"{MODELS}/99999999/meters", json={"meter_type_id": oil["id"]}).status_code == 404
        assert engineer.get(f"{MODELS}/99999999/meters").status_code == 404
        assert engineer.put(f"{MODEL_METERS}/99999999", json={"active": False}).status_code == 404

    def test_a_deactivated_meter_type_stays_and_its_limits_still_change(self, engineer, admin, make_model,
                                                                         make_meter_type):
        model, oil = make_model(), make_meter_type()
        row = _add(engineer, model, oil).get_json()
        admin.put(f"{BASE}/meter-types/{oil['id']}", json={"active": False})
        assert [r["id"] for r in engineer.get(_meters_url(model)).get_json()] == [row["id"]]
        assert engineer.put(f"{MODEL_METERS}/{row['id']}", json={"max_value": "5"}).status_code == 200

    def test_an_inactive_model_may_gain_change_and_lose_meters(self, engineer, make_model, make_meter_type):
        model = make_model()
        assert engineer.put(f"{MODELS}/{model['id']}", json={"active": False}).status_code == 200
        row = _add(engineer, model, make_meter_type(), max_value="60")
        assert row.status_code == 201
        row_id = row.get_json()["id"]
        assert engineer.put(f"{MODEL_METERS}/{row_id}", json={"max_value": "50"}).status_code == 200
        assert engineer.put(f"{MODEL_METERS}/{row_id}", json={"active": False}).status_code == 200

    def test_an_operator_reads_but_cannot_write(self, role_client, engineer, make_model, make_meter_type):
        operator = role_client("maint_operator")
        model, oil = make_model(), make_meter_type()
        row = _add(engineer, model, oil).get_json()
        assert operator.get(_meters_url(model)).status_code == 200
        assert _add(operator, model, make_meter_type()).status_code == 403
        assert operator.put(f"{MODEL_METERS}/{row['id']}", json={"active": False}).status_code == 403
