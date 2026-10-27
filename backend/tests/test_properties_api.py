"""Equipment properties (S043 § 5, § 6, § 8.2) — the property master, its options, the class
links and the models' values (S061: the flags, per-machine properties), against the test DB.  Needs the dev MariaDB container
(tooling/dev/dev-db-up.bat).  Names come from a counter of this module, never fixed values."""

import itertools

import pytest

from properties_core import (
    CHOOSE_ACTIVE_PROPERTIES, CHOOSE_A_PROPERTY, CHOOSE_OPTION, CHOOSE_YES_OR_NO, DATA_TYPE_FIXED, ENTER_NUMBER,
    NOT_ON_CLASS, ONLY_CHOICE_HAS_OPTIONS, PER_ITEM_HAS_MODEL_VALUES, SET_ON_EACH_MACHINE, UNIT_FIXED,
    UNIT_ONLY_NUMBER, VALUES_NOT_OBJECT,
)

BASE = "/api/masters"
PROPERTIES = f"{BASE}/properties"
OPTIONS = f"{BASE}/property-options"

_numbers = itertools.count(1)


def _name(prefix="Test property"):
    return f"{prefix} {next(_numbers):04d}"


def _class_path(cls):
    return f"{BASE}/equipment-classes/{cls['id']}/properties"


def _model_path(model):
    return f"{BASE}/equipment-models/{model['id']}/properties"


def _refusal(res):
    return res.status_code, res.get_json()


def _made(rows, *made):
    """The rows of the properties the test made, without the seed "GPS location" and other
    every-class properties, which show on every class since S061 (BR1-02)."""
    ids = {prop["id"] for prop in made}
    return [row for row in rows if row["property_id"] in ids]


@pytest.fixture
def make_property(engineer):
    """make_property() -> a number property in kW; data_type=, options=[...] etc. to choose."""
    def make(**overrides):
        body = {"name": _name(), "data_type": "number", "unit": "kW", **overrides}
        if body["data_type"] != "number":
            body.pop("unit")
        res = engineer.post(PROPERTIES, json=body)
        assert res.status_code == 201, res.get_json()
        return res.get_json()
    return make


@pytest.fixture
def link(engineer):
    def add(cls, *props):
        res = engineer.post(_class_path(cls), json={"property_ids": [p["id"] for p in props]})
        assert res.status_code == 200, res.get_json()
        return res.get_json()["items"]
    return add


def _listed(client, prop_id, query=""):
    items = client.get(f"{PROPERTIES}{query}").get_json()["items"]
    return next((item for item in items if item["id"] == prop_id), None)


class TestCreate:

    @pytest.mark.parametrize("data_type", ["number", "choice", "text", "yes_no"])
    def test_each_type(self, engineer, data_type):
        name = _name()
        body = {"name": f"  {name} ", "data_type": data_type, "description": " Where to read it "}
        res = engineer.post(PROPERTIES, json=body)
        assert res.status_code == 201, res.get_json()
        prop = res.get_json()
        assert (prop["name"], prop["data_type"], prop["unit"], prop["description"], prop["active"]) == (
            name, data_type, None, "Where to read it", 1)
        assert (prop["options"], prop["class_count"], prop["value_count"], prop["created_by"]) == (
            [], 0, 0, "test_maint_engineer")

    def test_a_number_with_its_unit_and_a_choice_with_options(self, engineer):
        res = engineer.post(PROPERTIES, json={"name": _name(), "data_type": "number", "unit": " cc/rev "})
        assert (res.status_code, res.get_json()["unit"]) == (201, "cc/rev")
        res = engineer.post(PROPERTIES, json={"name": _name(), "data_type": "choice",
                                              "options": ["Internal", "External"]})
        assert res.status_code == 201
        assert [(o["label"], o["active"]) for o in res.get_json()["options"]] == [("Internal", 1), ("External", 1)]

    def test_a_duplicate_name_by_case_is_409(self, engineer, make_property):
        prop = make_property()
        res = engineer.post(PROPERTIES, json={"name": prop["name"].upper(), "data_type": "text"})
        assert _refusal(res) == (409, {"error": "A property with this name exists", "field": "name"})

    def test_a_unit_on_a_choice_is_400(self, engineer):
        res = engineer.post(PROPERTIES, json={"name": _name(), "data_type": "choice", "unit": "kW"})
        assert _refusal(res) == (400, {"error": UNIT_ONLY_NUMBER, "field": "unit"})

    def test_listed_by_name_and_inactive_on_request(self, engineer, make_property):
        b = make_property(name=_name("Zz property b"))
        a = make_property(name=_name("Zz property a"))
        ids = [item["id"] for item in engineer.get(PROPERTIES).get_json()["items"]]
        assert ids.index(a["id"]) < ids.index(b["id"])
        assert engineer.put(f"{PROPERTIES}/{a['id']}", json={"active": False}).status_code == 200
        assert _listed(engineer, a["id"]) is None
        assert _listed(engineer, a["id"], "?include_inactive=1")["active"] == 0


class TestEdit:

    def test_type_and_unit_change_while_unused(self, engineer, make_property):
        prop = make_property()
        res = engineer.put(f"{PROPERTIES}/{prop['id']}", json={"unit": "W"})
        assert (res.status_code, res.get_json()["unit"]) == (200, "W")
        res = engineer.put(f"{PROPERTIES}/{prop['id']}", json={"data_type": "text"})
        assert (res.status_code, res.get_json()["data_type"], res.get_json()["unit"]) == (200, "text", None)
        res = engineer.put(f"{PROPERTIES}/{prop['id']}", json={"data_type": "choice"})
        assert (res.status_code, res.get_json()["data_type"]) == (200, "choice")

    def test_a_unit_on_a_text_property_is_400(self, engineer, make_property):
        prop = make_property(data_type="text")
        res = engineer.put(f"{PROPERTIES}/{prop['id']}", json={"unit": "kW"})
        assert _refusal(res) == (400, {"error": UNIT_ONLY_NUMBER, "field": "unit"})

    def test_a_choice_with_an_option_keeps_its_type(self, engineer, make_property):
        prop = make_property(data_type="choice", options=["A"])
        engineer.put(f"{OPTIONS}/{prop['options'][0]['id']}", json={"active": False})   # an inactive one counts
        res = engineer.put(f"{PROPERTIES}/{prop['id']}", json={"data_type": "text"})
        assert _refusal(res) == (409, {"error": DATA_TYPE_FIXED, "field": "data_type"})

    def test_a_number_with_a_value_keeps_type_and_unit(self, engineer, make_property, make_model, link):
        prop = make_property()
        model = make_model()
        link({"id": model["class_id"]}, prop)
        assert engineer.put(_model_path(model), json={"values": {str(prop["id"]): "7.5"}}).status_code == 200
        assert _listed(engineer, prop["id"])["value_count"] == 1
        res = engineer.put(f"{PROPERTIES}/{prop['id']}", json={"data_type": "text"})
        assert _refusal(res) == (409, {"error": DATA_TYPE_FIXED, "field": "data_type"})
        res = engineer.put(f"{PROPERTIES}/{prop['id']}", json={"unit": "W"})
        assert _refusal(res) == (409, {"error": UNIT_FIXED, "field": "unit"})
        # The name and description still change
        res = engineer.put(f"{PROPERTIES}/{prop['id']}", json={"name": _name(), "unit": "kW"})
        assert res.status_code == 200

    def test_an_item_s_own_value_keeps_type_and_unit_and_counts_hidden_too(self, admin, engineer, make_property,
                                                                          make_equipment, link):
        """S044 § 1.6: a property with only an item's value is frozen as one with a model's, and a
        value hidden by unlinking still freezes it and counts."""
        prop = make_property()
        node = make_equipment()
        cls = {"id": node["class_id"]}
        link(cls, prop)
        res = admin.put(f"/api/equipment/{node['id']}/properties", json={"values": {str(prop["id"]): "5.5"}})
        assert res.status_code == 200, res.get_json()
        assert _listed(engineer, prop["id"])["value_count"] == 1
        assert engineer.delete(f"{_class_path(cls)}/{prop['id']}").status_code == 200   # hidden, kept
        assert _listed(engineer, prop["id"])["value_count"] == 1
        res = engineer.put(f"{PROPERTIES}/{prop['id']}", json={"data_type": "text"})
        assert _refusal(res) == (409, {"error": DATA_TYPE_FIXED, "field": "data_type"})
        res = engineer.put(f"{PROPERTIES}/{prop['id']}", json={"unit": "W"})
        assert _refusal(res) == (409, {"error": UNIT_FIXED, "field": "unit"})

    def test_the_freeze_texts(self):
        """S044 § 1.6 (BR1-08): the texts name values, not only models'."""
        assert DATA_TYPE_FIXED == ("The data type cannot be changed: the property has options or values. "
                                   "Make a new property instead.")
        assert UNIT_FIXED == "The unit cannot be changed: the property has values. Make a new property instead."

    def test_a_wrong_type_is_400_on_its_field(self, engineer, make_property):
        prop = make_property()
        assert _refusal(engineer.put(f"{PROPERTIES}/{prop['id']}", json={"name": 5})) == (
            400, {"error": "Enter a name", "field": "name"})
        assert engineer.put(f"{PROPERTIES}/{prop['id']}", json={"active": "no"}).get_json()["field"] == "active"

    def test_unknown_is_404(self, engineer):
        assert engineer.put(f"{PROPERTIES}/999999999", json={"name": _name()}).status_code == 404


class TestOptions:

    def test_add_rename_deactivate(self, engineer, make_property):
        prop = make_property(data_type="choice")
        res = engineer.post(f"{PROPERTIES}/{prop['id']}/options", json={"label": "  Packed   gland "})
        assert res.status_code == 201
        option = res.get_json()
        assert (option["label"], option["active"], option["property_id"]) == ("Packed gland", 1, prop["id"])
        res = engineer.put(f"{OPTIONS}/{option['id']}", json={"label": "Packed seal", "active": False})
        assert (res.status_code, res.get_json()["label"], res.get_json()["active"]) == (200, "Packed seal", 0)

    def test_only_a_choice_has_options(self, engineer, make_property):
        prop = make_property()
        res = engineer.post(f"{PROPERTIES}/{prop['id']}/options", json={"label": "A"})
        assert _refusal(res) == (400, {"error": ONLY_CHOICE_HAS_OPTIONS, "field": "label"})

    def test_a_duplicate_label_is_409(self, engineer, make_property):
        prop = make_property(data_type="choice", options=["Internal"])
        res = engineer.post(f"{PROPERTIES}/{prop['id']}/options", json={"label": "INTERNAL"})
        assert _refusal(res) == (409, {"error": "An option with this label exists", "field": "label"})

    def test_an_inactive_option_is_refused_new_but_kept_unchanged(self, engineer, make_property, make_model, link):
        prop = make_property(data_type="choice", options=["Internal", "External"])
        internal, external = prop["options"]
        model, other = make_model(), None
        other = make_model(cls={"id": model["class_id"]})
        link({"id": model["class_id"]}, prop)
        key = str(prop["id"])
        assert engineer.put(_model_path(model), json={"values": {key: internal["id"]}}).status_code == 200
        engineer.put(f"{OPTIONS}/{internal['id']}", json={"active": False})
        # Still shown, and the model's dialog still offers it beside the active one
        item = engineer.get(_model_path(model)).get_json()["items"][0]
        assert (item["display"], [o["label"] for o in item["options"]]) == ("Internal", ["Internal", "External"])
        assert engineer.put(_model_path(model), json={"values": {key: internal["id"]}}).status_code == 200
        res = engineer.put(_model_path(other), json={"values": {key: internal["id"]}})
        assert _refusal(res) == (400, {"error": CHOOSE_OPTION, "field": f"values.{key}"})
        assert [o["label"] for o in engineer.get(_model_path(other)).get_json()["items"][0]["options"]] == ["External"]

    def test_another_propertys_option_is_refused(self, engineer, make_property, make_model, link):
        prop = make_property(data_type="choice", options=["A"])
        stranger = make_property(data_type="choice", options=["B"])
        model = make_model()
        link({"id": model["class_id"]}, prop)
        res = engineer.put(_model_path(model), json={"values": {str(prop["id"]): stranger["options"][0]["id"]}})
        assert _refusal(res) == (400, {"error": CHOOSE_OPTION, "field": f"values.{prop['id']}"})


class TestClassLinks:

    def test_add_two_at_once_and_skip_one_already_there(self, engineer, make_class, make_property):
        cls = make_class()
        a, b = make_property(name=_name("Link a")), make_property(name=_name("Link b"))
        res = engineer.post(_class_path(cls), json={"property_ids": [b["id"], a["id"], b["id"]]})
        assert res.status_code == 200
        items = _made(res.get_json()["items"], a, b)
        assert [i["property_id"] for i in items] == [a["id"], b["id"]]
        assert items[0] == {"property_id": a["id"], "name": a["name"], "data_type": "number", "unit": "kW",
                            "active": 1, "all_classes": False}
        res = engineer.post(_class_path(cls), json={"property_ids": [a["id"]]})
        assert (res.status_code, len(_made(res.get_json()["items"], a, b))) == (200, 2)
        assert _listed(engineer, a["id"])["class_count"] == 1

    @pytest.mark.parametrize("body", [{"property_ids": []}, {"property_ids": "1"}, {"property_ids": [True]},
                                      {}, {"property_ids": ["1"]}])
    def test_an_empty_or_wrong_list_is_400(self, engineer, make_class, body):
        res = engineer.post(_class_path(make_class()), json=body)
        assert _refusal(res) == (400, {"error": CHOOSE_A_PROPERTY, "field": "property_ids"})

    def test_inactive_unknown_or_optionless_choice_is_400(self, engineer, make_class, make_property):
        cls = make_class()
        inactive = make_property()
        engineer.put(f"{PROPERTIES}/{inactive['id']}", json={"active": False})
        no_options = make_property(data_type="choice")
        retired = make_property(data_type="choice", options=["A"])
        engineer.put(f"{OPTIONS}/{retired['options'][0]['id']}", json={"active": False})
        for ids in ([inactive["id"]], [no_options["id"]], [retired["id"]], [999999999]):
            res = engineer.post(_class_path(cls), json={"property_ids": ids})
            assert _refusal(res) == (400, {"error": CHOOSE_ACTIVE_PROPERTIES, "field": "property_ids"})
        assert _made(engineer.get(_class_path(cls)).get_json()["items"], inactive, no_options, retired) == []

    def test_an_inactive_class_gets_them(self, engineer, make_class, make_property, link):
        cls = make_class()
        assert engineer.put(f"{BASE}/equipment-classes/{cls['id']}", json={"active": False}).status_code == 200
        prop = make_property()
        assert len(_made(link(cls, prop), prop)) == 1

    def test_remove_keeps_the_values_and_adding_again_shows_them(self, engineer, make_model, make_property, link):
        model = make_model()
        cls = {"id": model["class_id"]}
        prop = make_property()
        link(cls, prop)
        engineer.put(_model_path(model), json={"values": {str(prop["id"]): "62.5"}})
        res = engineer.delete(f"{_class_path(cls)}/{prop['id']}")
        assert (res.status_code, _made(res.get_json()["items"], prop)) == (200, [])
        assert _made(engineer.get(_model_path(model)).get_json()["items"], prop) == []
        assert _listed(engineer, prop["id"])["value_count"] == 1
        link(cls, prop)
        assert _made(engineer.get(_model_path(model)).get_json()["items"], prop)[0]["display"] == "62.5 kW"

    def test_remove_one_not_on_the_class_is_404(self, engineer, make_class, make_property):
        res = engineer.delete(f"{_class_path(make_class())}/{make_property()['id']}")
        assert res.status_code == 404

    def test_an_inactive_linked_property_stays_listed_and_can_be_removed(self, engineer, make_class, make_property,
                                                                         link):
        cls = make_class()
        prop = make_property()
        link(cls, prop)
        engineer.put(f"{PROPERTIES}/{prop['id']}", json={"active": False})
        items = _made(engineer.get(_class_path(cls)).get_json()["items"], prop)
        assert [(i["property_id"], i["active"]) for i in items] == [(prop["id"], 0)]
        assert engineer.delete(f"{_class_path(cls)}/{prop['id']}").status_code == 200

    def test_unknown_class_is_404(self, engineer, make_property):
        path = f"{BASE}/equipment-classes/999999999/properties"
        assert engineer.get(path).status_code == 404
        assert engineer.post(path, json={"property_ids": [make_property()["id"]]}).status_code == 404


class TestModelValues:

    @pytest.fixture
    def setup(self, make_model, make_property, link):
        """A model whose class has one property of each type."""
        model = make_model()
        props = {
            "number": make_property(name=_name("Mv a number"), unit="kVA"),
            "choice": make_property(name=_name("Mv b choice"), data_type="choice", options=["Internal", "External"]),
            "text": make_property(name=_name("Mv c text"), data_type="text"),
            "yes_no": make_property(name=_name("Mv d yes"), data_type="yes_no"),
        }
        link({"id": model["class_id"]}, *props.values())
        return model, props

    def test_set_each_type_and_clear(self, engineer, setup):
        model, props = setup
        internal = props["choice"]["options"][0]["id"]
        values = {str(props["number"]["id"]): "62.50", str(props["choice"]["id"]): internal,
                  str(props["text"]["id"]): " IP55 ", str(props["yes_no"]["id"]): True}
        res = engineer.put(_model_path(model), json={"values": values})
        assert res.status_code == 200, res.get_json()
        items = res.get_json()["items"]
        assert [(i["data_type"], i["value"], i["display"]) for i in items] == [
            ("number", "62.5", "62.5 kVA"), ("choice", internal, "Internal"), ("text", "IP55", "IP55"),
            ("yes_no", True, "Yes")]
        assert items[0]["unit"] == "kVA" and [o["label"] for o in items[1]["options"]] == ["Internal", "External"]
        # Clear by null and by "": the others stay
        res = engineer.put(_model_path(model), json={"values": {str(props["number"]["id"]): None,
                                                                str(props["text"]["id"]): ""}})
        assert [i["display"] for i in res.get_json()["items"]] == [None, "Internal", None, "Yes"]
        assert engineer.get(_model_path(model)).get_json() == res.get_json()

    def test_values_shape(self, engineer, setup):
        model, props = setup
        assert _refusal(engineer.put(_model_path(model), json={"values": []})) == (
            400, {"error": VALUES_NOT_OBJECT, "field": "values"})
        assert _refusal(engineer.put(_model_path(model), json={})) == (
            400, {"error": VALUES_NOT_OBJECT, "field": "values"})
        assert engineer.put(_model_path(model), json={"values": {}}).status_code == 200
        assert _refusal(engineer.put(_model_path(model), json={"values": {"abc": 1}})) == (
            400, {"error": NOT_ON_CLASS, "field": "values.abc"})

    def test_a_property_not_on_the_class_is_400(self, engineer, setup, make_property):
        model, _props = setup
        stranger = make_property()
        res = engineer.put(_model_path(model), json={"values": {str(stranger["id"]): "1"}})
        assert _refusal(res) == (400, {"error": NOT_ON_CLASS, "field": f"values.{stranger['id']}"})
        res = engineer.put(_model_path(model), json={"values": {"999999999": "1"}})
        assert _refusal(res) == (400, {"error": NOT_ON_CLASS, "field": "values.999999999"})

    def test_two_wrong_values_the_first_by_name_answers_and_nothing_is_saved(self, engineer, setup):
        model, props = setup
        values = {str(props["yes_no"]["id"]): "yes", str(props["number"]["id"]): "abc",
                  str(props["text"]["id"]): "kept?"}
        res = engineer.put(_model_path(model), json={"values": values})
        assert _refusal(res) == (400, {"error": ENTER_NUMBER, "field": f"values.{props['number']['id']}"})
        assert all(i["value"] is None for i in engineer.get(_model_path(model)).get_json()["items"])

    def test_an_inactive_model_may_be_edited(self, engineer, setup):
        model, props = setup
        assert engineer.put(f"{BASE}/equipment-models/{model['id']}", json={"active": False}).status_code == 200
        res = engineer.put(_model_path(model), json={"values": {str(props["text"]["id"]): "132M"}})
        assert res.status_code == 200

    def test_an_inactive_property_is_hidden_and_refused(self, engineer, setup):
        model, props = setup
        engineer.put(f"{PROPERTIES}/{props['text']['id']}", json={"active": False})
        assert props["text"]["id"] not in [i["property_id"] for i in engineer.get(_model_path(model)).get_json()["items"]]
        res = engineer.put(_model_path(model), json={"values": {str(props["text"]["id"]): "x"}})
        assert res.status_code == 400

    def test_unknown_model_is_404(self, engineer):
        assert engineer.get(f"{BASE}/equipment-models/999999999/properties").status_code == 404
        assert engineer.put(f"{BASE}/equipment-models/999999999/properties", json={"values": {}}).status_code == 404


class TestPermissions:

    def test_an_operator_reads_but_never_writes(self, role_client, engineer, make_model, make_property, link):
        operator = role_client("maint_operator")
        model = make_model()
        prop = make_property(data_type="choice", options=["A"])
        cls = {"id": model["class_id"]}
        link(cls, prop)
        for path in (PROPERTIES, _class_path(cls), _model_path(model)):
            assert operator.get(path).status_code == 200
        writes = [
            operator.post(PROPERTIES, json={"name": _name(), "data_type": "text"}),
            operator.put(f"{PROPERTIES}/{prop['id']}", json={"name": _name()}),
            operator.post(f"{PROPERTIES}/{prop['id']}/options", json={"label": "B"}),
            operator.put(f"{OPTIONS}/{prop['options'][0]['id']}", json={"label": "C"}),
            operator.post(_class_path(cls), json={"property_ids": [prop["id"]]}),
            operator.delete(f"{_class_path(cls)}/{prop['id']}"),
            operator.put(_model_path(model), json={"values": {}}),
        ]
        assert [res.status_code for res in writes] == [403] * len(writes)

    def test_an_engineer_at_one_site_writes(self, user_at_sites, make_site, make_unit, make_model):
        site = make_site()
        engineer, _ = user_at_sites([(site, "maint_engineer", [make_unit(site)])])
        res = engineer.post(PROPERTIES, json={"name": _name(), "data_type": "number", "unit": "bar"})
        assert res.status_code == 201
        prop = res.get_json()
        model = make_model()
        assert engineer.post(_class_path({"id": model["class_id"]}), json={"property_ids": [prop["id"]]}).status_code == 200
        assert engineer.put(_model_path(model), json={"values": {str(prop["id"]): "250"}}).status_code == 200


class TestDatabaseDown:

    def test_a_write_and_a_read_are_503(self, admin, db_down):
        assert admin.get(PROPERTIES).status_code == 503
        assert admin.post(PROPERTIES, json={"name": _name(), "data_type": "text"}).status_code == 503


# ---------------------------------------------------------------------------
# S061: the flags, per-machine properties and the class table (§ 5.1, § 5.3, § 5.4, § 8.2)
# ---------------------------------------------------------------------------

# every_class: conftest.py's, which takes this module's make_property (S062 BS1-02)


class TestFlags:

    def test_create_and_list_carry_the_flags(self, engineer, make_property):
        plain = make_property()
        geo = make_property(data_type="geo", per_item_only=True)
        assert (plain["all_classes"], plain["per_item_only"]) == (0, 0)
        assert (geo["data_type"], geo["unit"], geo["per_item_only"], geo["all_classes"]) == ("geo", None, 1, 0)
        listed = _listed(engineer, geo["id"])
        assert (listed["all_classes"], listed["per_item_only"]) == (0, 1)

    def test_a_flag_that_is_not_yes_or_no_is_400(self, engineer, make_property):
        res = engineer.put(f"{PROPERTIES}/{make_property()['id']}", json={"per_item_only": "yes"})
        assert _refusal(res) == (400, {"error": CHOOSE_YES_OR_NO, "field": "per_item_only"})

    def test_per_item_only_on_is_409_while_a_model_has_a_value(self, engineer, make_model, make_property, link):
        model = make_model()
        prop = make_property()
        link({"id": model["class_id"]}, prop)
        assert engineer.put(_model_path(model), json={"values": {str(prop["id"]): "7.5"}}).status_code == 200
        res = engineer.put(f"{PROPERTIES}/{prop['id']}", json={"per_item_only": True})
        assert _refusal(res) == (409, {"error": PER_ITEM_HAS_MODEL_VALUES, "field": "per_item_only"})
        assert engineer.put(_model_path(model), json={"values": {str(prop["id"]): None}}).status_code == 200
        res = engineer.put(f"{PROPERTIES}/{prop['id']}", json={"per_item_only": True})
        assert (res.status_code, res.get_json()["per_item_only"]) == (200, 1)
        # Off again at any time
        assert engineer.put(f"{PROPERTIES}/{prop['id']}", json={"per_item_only": False}).status_code == 200


class TestPerMachine:

    def test_absent_from_the_model_dialog_and_refused_on_a_model_save(self, engineer, make_model, make_property,
                                                                      link):
        model = make_model()
        prop = make_property(per_item_only=True)
        link({"id": model["class_id"]}, prop)
        assert prop["id"] not in [i["property_id"] for i in engineer.get(_model_path(model)).get_json()["items"]]
        res = engineer.put(_model_path(model), json={"values": {str(prop["id"]): "7.5"}})
        assert _refusal(res) == (400, {"error": SET_ON_EACH_MACHINE, "field": f"values.{prop['id']}"})

    def test_the_seed_is_left_out_of_every_model_dialog(self, engineer, make_model):
        gps = next(p for p in engineer.get(PROPERTIES).get_json()["items"] if p["name"] == "GPS location")
        assert (gps["data_type"], gps["all_classes"], gps["per_item_only"]) == ("geo", 1, 1)
        model = make_model()
        assert gps["id"] not in [i["property_id"] for i in engineer.get(_model_path(model)).get_json()["items"]]
        res = engineer.put(_model_path(model), json={"values": {str(gps["id"]): "11, 76"}})
        assert _refusal(res) == (400, {"error": SET_ON_EACH_MACHINE, "field": f"values.{gps['id']}"})


class TestClassTable:

    def test_every_class_rows_are_marked_and_listed_once(self, engineer, make_class, make_property, every_class,
                                                         link):
        cls = make_class()
        linked, both = make_property(), every_class()
        items = link(cls, linked, both)   # the answer of Add carries the every-class rows too (BR2-01)
        # By name: linked was made first, so its counter is lower
        assert [(i["property_id"], i["all_classes"]) for i in _made(items, linked, both)] == [
            (linked["id"], False), (both["id"], True)]
        listed = engineer.get(_class_path(cls)).get_json()["items"]
        assert [i["property_id"] for i in listed].count(both["id"]) == 1
        gps = next(i for i in listed if i["name"] == "GPS location")
        assert gps["all_classes"] is True
        # The answer of Remove carries them too
        res = engineer.delete(f"{_class_path(cls)}/{linked['id']}")
        assert both["id"] in [i["property_id"] for i in res.get_json()["items"]]
