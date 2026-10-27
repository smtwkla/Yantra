"""The equipment list's property filter (S062 § 5, § 8.2): GET /api/equipment and
GET /api/equipment/asset-list with ``props``, against the test DB.  Every test makes its own class,
properties, models and machines in a fresh unit, and names the unit in its query, so the seed
"GPS location" and other tests' rows never match."""

import json

import pytest

from properties_core import ENTER_NUMBER
from property_filter_core import PROPERTY_NOT_IN_USE, UNREADABLE

EQUIPMENT = "/api/equipment"
ASSET_LIST = f"{EQUIPMENT}/asset-list"
MASTERS = "/api/masters"
GPS = "GPS location"


def _props(*rules, match="all"):
    return json.dumps({"match": match, "rules": list(rules)})


def _rule(prop, op, value=None):
    rule = {"property_id": prop["id"], "op": op}
    if value is not None:
        rule["value"] = value
    return rule


def _ok(res, status=200):
    assert res.status_code == status, res.get_json()
    return res.get_json()


def _codes(client, props, **query):
    """The codes the list answers, all levels unless ``level`` is given."""
    body = _ok(client.get(EQUIPMENT, query_string={"props": props, "level": "all", "per_page": 200, **query}))
    return sorted(item["code"] for item in body["items"])


def _sorted(*nodes):
    return sorted(node["code"] for node in nodes)


def _set_model(admin, model, values):
    _ok(admin.put(f"{MASTERS}/equipment-models/{model['id']}/properties",
                  json={"values": {str(p["id"]): v for p, v in values}}))


def _set_own(admin, node, values):
    _ok(admin.put(f"{EQUIPMENT}/{node['id']}/properties", json={"values": {str(p["id"]): v for p, v in values}}))


def _no_model_part(admin, parent, cls, name="Rewound motor"):
    return _ok(admin.post(EQUIPMENT, json={"level": "component_unit", "parent_id": parent["id"], "model_id": None,
                                           "class_id": cls["id"], "name": name}), 201)


@pytest.fixture
def cls(make_class):
    return make_class()


@pytest.fixture
def power(make_property, link, cls):
    """A number property in kW, linked to ``cls``."""
    prop = make_property("Rated power")
    link(cls["id"], prop)
    return prop


@pytest.fixture
def machines(admin, make_model, make_equipment, cls, power, unit):
    """Two machines of ``cls`` in ``unit``: ``small`` of a 7.5 kW model, ``big`` of a 15 kW model."""
    small_model, big_model = make_model(cls=cls), make_model(cls=cls)
    _set_model(admin, small_model, [(power, "7.5")])
    _set_model(admin, big_model, [(power, "15")])
    return {"small": make_equipment(unit=unit, model=small_model), "big": make_equipment(unit=unit, model=big_model)}


@pytest.fixture
def mount(make_property, link, cls):
    """A choice property linked to ``cls`` (never named Mobility: that name is the hint's, S061)."""
    prop = make_property("Mount", data_type="choice", options=["Fixed", "Mobile", "Portable"])
    link(cls["id"], prop)
    return prop


def _option(prop, label):
    return next(o["id"] for o in prop["options"] if o["label"] == label)


class TestNumber:

    def test_more_than_and_between(self, admin, machines, power, unit):
        assert _codes(admin, _props(_rule(power, "gt", "10")), unit_id=unit["id"]) == _sorted(machines["big"])
        assert _codes(admin, _props(_rule(power, "between", ["5", "10"])), unit_id=unit["id"]) == (
            _sorted(machines["small"]))

    def test_the_item_s_own_value_wins(self, admin, machines, power, unit):
        _set_own(admin, machines["small"], [(power, "15")])
        assert _codes(admin, _props(_rule(power, "gt", "10")), unit_id=unit["id"]) == (
            _sorted(machines["small"], machines["big"]))
        assert _codes(admin, _props(_rule(power, "eq", "7.5")), unit_id=unit["id"]) == []

    def test_a_component_unit_without_a_model_matches_by_its_own_value(self, admin, machines, power, cls, unit):
        part = _no_model_part(admin, machines["small"], cls)
        _set_own(admin, part, [(power, "30")])
        assert _codes(admin, _props(_rule(power, "gt", "20")), unit_id=unit["id"]) == _sorted(part)
        # The level filter still applies: the default level lists machines only
        body = _ok(admin.get(EQUIPMENT, query_string={"props": _props(_rule(power, "gt", "20")), "unit_id": unit["id"]}))
        assert body["items"] == []


class TestChoice:

    def test_is_and_is_not(self, admin, make_equipment, make_model, cls, mount, unit):
        nodes = {label: make_equipment(unit=unit, model=make_model(cls=cls)) for label in ("Portable", "Mobile", "Fixed")}
        bare = make_equipment(unit=unit, model=make_model(cls=cls))
        for label, node in nodes.items():
            _set_own(admin, node, [(mount, _option(mount, label))])
        moving = [_option(mount, "Portable"), _option(mount, "Mobile")]
        assert _codes(admin, _props(_rule(mount, "in", moving)), unit_id=unit["id"]) == (
            _sorted(nodes["Portable"], nodes["Mobile"]))
        # A machine with no value is not "is not Fixed" (D4); "has no value" with Any adds it
        assert _codes(admin, _props(_rule(mount, "not_in", [_option(mount, "Fixed")])), unit_id=unit["id"]) == (
            _sorted(nodes["Portable"], nodes["Mobile"]))
        assert _codes(admin, _props(_rule(mount, "not_in", [_option(mount, "Fixed")]), _rule(mount, "none"),
                                    match="any"), unit_id=unit["id"]) == _sorted(nodes["Portable"], nodes["Mobile"], bare)


class TestApplies:

    def test_has_no_value_lists_the_linked_class_only(self, admin, make_equipment, make_class, power, machines, unit):
        other_class_machine = make_equipment(unit=unit, cls=make_class())
        same_class_bare = make_equipment(unit=unit, cls={"id": machines["small"]["class_id"]})
        assert _codes(admin, _props(_rule(power, "none")), unit_id=unit["id"]) == _sorted(same_class_bare)
        assert other_class_machine["code"] not in _codes(admin, _props(_rule(power, "none")), unit_id=unit["id"])

    def test_a_hidden_own_value_does_not_match(self, admin, machines, power, cls, unit):
        _set_own(admin, machines["small"], [(power, "99")])
        assert _codes(admin, _props(_rule(power, "gt", "50")), unit_id=unit["id"]) == _sorted(machines["small"])
        _ok(admin.delete(f"{MASTERS}/equipment-classes/{cls['id']}/properties/{power['id']}"))
        assert _codes(admin, _props(_rule(power, "has")), unit_id=unit["id"]) == []
        assert _codes(admin, _props(_rule(power, "none")), unit_id=unit["id"]) == []

    def test_an_every_class_property_matches_a_machine_of_a_class_without_links(self, admin, make_equipment,
                                                                               every_class, unit):
        shared = every_class("S062 every", data_type="yes_no")
        yes, no = make_equipment(unit=unit), make_equipment(unit=unit)
        _set_own(admin, yes, [(shared, True)])
        _set_own(admin, no, [(shared, False)])
        assert _codes(admin, _props(_rule(shared, "eq", True)), unit_id=unit["id"]) == _sorted(yes)
        assert _codes(admin, _props(_rule(shared, "eq", False)), unit_id=unit["id"]) == _sorted(no)

    def test_a_location_matches_top_level_machines_only(self, admin, machines, cls, unit):
        gps = next(p for p in _ok(admin.get(f"{MASTERS}/properties"))["items"] if p["name"] == GPS)
        part = _no_model_part(admin, machines["small"], cls)
        _set_own(admin, machines["small"], [(gps, "11.016823, 76.955812")])
        assert _codes(admin, _props(_rule(gps, "has")), unit_id=unit["id"]) == _sorted(machines["small"])
        # The part shows no Location (a part is where its machine is), so it is not a gap either
        assert _codes(admin, _props(_rule(gps, "none")), unit_id=unit["id"]) == _sorted(machines["big"])
        assert part["code"] not in _codes(admin, _props(_rule(gps, "none")), unit_id=unit["id"])


class TestCombined:

    def test_all_and_any(self, admin, machines, power, mount, unit):
        _set_own(admin, machines["small"], [(mount, _option(mount, "Portable"))])
        rules = (_rule(power, "gt", "10"), _rule(mount, "in", [_option(mount, "Portable")]))
        assert _codes(admin, _props(*rules), unit_id=unit["id"]) == []
        assert _codes(admin, _props(*rules, match="any"), unit_id=unit["id"]) == (
            _sorted(machines["small"], machines["big"]))
        _set_own(admin, machines["big"], [(mount, _option(mount, "Portable"))])
        assert _codes(admin, _props(*rules), unit_id=unit["id"]) == _sorted(machines["big"])

    def test_the_class_filter_and_the_search_join_with_and(self, admin, make_equipment, make_model, make_class, link,
                                                           machines, power, cls, unit):
        other = make_class()
        link(other["id"], power)
        other_model = make_model(cls=other)
        _set_model(admin, other_model, [(power, "15")])
        other_big = make_equipment(unit=unit, model=other_model, name="Searchable press")
        props = _props(_rule(power, "gt", "10"))
        assert _codes(admin, props, unit_id=unit["id"]) == _sorted(machines["big"], other_big)
        assert _codes(admin, props, unit_id=unit["id"], class_id=other["id"]) == _sorted(other_big)
        assert _codes(admin, props, unit_id=unit["id"], q="Searchable") == _sorted(other_big)

    def test_text_contains_matches_percent_and_underscore_literally(self, admin, make_property, link, make_equipment,
                                                                    make_model, cls, unit):
        frame = make_property("Frame", data_type="text")
        link(cls["id"], frame)
        literal, wild = make_equipment(unit=unit, model=make_model(cls=cls)), make_equipment(
            unit=unit, model=make_model(cls=cls))
        _set_own(admin, literal, [(frame, "50%_x")])
        _set_own(admin, wild, [(frame, "50abx")])
        assert _codes(admin, _props(_rule(frame, "contains", "%_")), unit_id=unit["id"]) == _sorted(literal)
        assert _codes(admin, _props(_rule(frame, "eq", "50ABX")), unit_id=unit["id"]) == _sorted(wild)   # any case


class TestAccess:

    def test_a_user_of_one_unit_gets_only_that_unit_s_matches(self, admin, user_with_units, make_unit, make_equipment,
                                                              make_model, cls, power):
        mine, theirs = make_unit(), make_unit()
        model = make_model(cls=cls)
        _set_model(admin, model, [(power, "15")])
        here, there = make_equipment(unit=mine, model=model), make_equipment(unit=theirs, model=model)
        engineer = user_with_units("maint_engineer", [mine])
        assert _codes(engineer, _props(_rule(power, "gt", "10"))) == _sorted(here)
        assert _codes(admin, _props(_rule(power, "gt", "10"))) == _sorted(here, there)

    def test_a_user_with_no_units_gets_400_for_a_bad_filter(self, user_with_units, power):
        nobody = user_with_units("maint_engineer", [])
        res = nobody.get(EQUIPMENT, query_string={"props": "{broken", "per_page": 1})
        assert (res.status_code, res.get_json()) == (400, {"error": UNREADABLE, "field": "props"})
        assert _codes(nobody, _props(_rule(power, "has"))) == []

    def test_the_refusal_names_the_line_and_its_field(self, admin, power, make_property):
        old = make_property("Old")
        _ok(admin.put(f"{MASTERS}/properties/{old['id']}", json={"active": False}))
        res = admin.get(EQUIPMENT, query_string={"props": _props(_rule(power, "has"), _rule(power, "gt", "7,5")),
                                                 "level": "all", "per_page": 1})
        assert (res.status_code, res.get_json()) == (400, {"error": ENTER_NUMBER, "field": "props.rules.1.value"})
        res = admin.get(EQUIPMENT, query_string={"props": _props(_rule(old, "has"))})
        assert (res.status_code, res.get_json()) == (400, {"error": PROPERTY_NOT_IN_USE,
                                                            "field": "props.rules.0.property_id"})

    def test_database_down_is_503(self, admin, db_down):
        res = admin.get(EQUIPMENT, query_string={"props": _props({"property_id": 1, "op": "has"})})
        assert res.status_code == 503


class TestAssetList:

    def _codes(self, client, **query):
        res = client.get(ASSET_LIST, query_string=query)
        assert res.status_code == 200, res.get_json()
        return sorted(row["code"] for unit in res.get_json()["units"] for row in unit["rows"])

    def test_the_filter_chooses_machines_and_parts_come_with_them(self, admin, make_equipment, machines, power, unit):
        # The gearbox's class has no Rated power, so it would match no line of its own
        gearbox = make_equipment(parent=machines["big"], name="Gearbox")
        props = _props(_rule(power, "gt", "10"))
        assert self._codes(admin, unit_id=unit["id"], props=props) == _sorted(machines["big"])
        assert self._codes(admin, unit_id=unit["id"], props=props, with_parts=1) == _sorted(machines["big"], gearbox)

    def test_a_part_s_own_match_does_not_print_its_machine(self, admin, machines, power, cls, unit):
        part = _no_model_part(admin, machines["small"], cls)
        _set_own(admin, part, [(power, "30")])
        assert self._codes(admin, unit_id=unit["id"], props=_props(_rule(power, "gt", "20")), with_parts=1) == []

    def test_a_user_with_no_units_gets_400_for_a_bad_filter(self, user_with_units):
        # Guards the existing order: the filter is read before the unit check (brief 5.5)
        nobody = user_with_units("maint_engineer", [])
        res = nobody.get(ASSET_LIST, query_string={"props": "{broken"})
        assert (res.status_code, res.get_json()) == (400, {"error": UNREADABLE, "field": "props"})

    def test_a_bad_filter_is_400(self, admin):
        res = admin.get(ASSET_LIST, query_string={"props": json.dumps({"match": "any", "rules": [{"property_id": "x"}]})})
        assert (res.status_code, res.get_json()) == (400, {"error": UNREADABLE, "field": "props.rules.0"})
