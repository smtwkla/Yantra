"""An equipment item's own property values (S044 § 5, § 6, § 8.2): GET and PUT
/api/equipment/<id>/properties, the card's rows and the history, against the test DB.  Needs the
dev MariaDB container (tooling/dev/dev-db-up.bat).  Every test makes its own properties, classes,
models and nodes; names come from a counter of this module."""

import itertools

import pytest

from properties_core import (
    CHOOSE_OPTION, CHOOSE_YES_NO, ENTER_NUMBER, NOT_ON_CLASS, TEXT_TOO_LONG, TOO_MANY_DECIMALS, VALUES_NOT_OBJECT,
)

EQUIPMENT = "/api/equipment"
MASTERS = "/api/masters"
SCRAPPED = "This record is scrapped and cannot be changed"

_numbers = itertools.count(1)


def _url(node):
    return f"{EQUIPMENT}/{node['id']}/properties"


def _ok(res, status=200):
    assert res.status_code == status, res.get_json()
    return res.get_json()


def _refusal(res):
    body = res.get_json()
    return res.status_code, body.get("field"), body["error"]


def _events(admin, node):
    """The node's property history lines, oldest first."""
    events = _ok(admin.get(f"{EQUIPMENT}/{node['id']}"))["events"]
    return [(e["old_value"], e["new_value"]) for e in reversed(events) if e["event"] == "property"]


def _card(admin, node):
    """The detail's Properties card: {name: (display, source)}."""
    return {p["name"]: (p["display"], p["source"]) for p in _ok(admin.get(f"{EQUIPMENT}/{node['id']}"))["properties"]}


def _made(rows, *made):
    """The rows of the properties the test made, without the seed "GPS location" and other
    every-class properties, which show on every top-level machine since S061 (BR1-02)."""
    ids = {prop["id"] for prop in made}
    return [row for row in rows if row["property_id"] in ids]


def _own_rows(db_rows, node):
    return list(db_rows("SELECT property_id, value_number, value_text, value_bool, option_id, updated_at, updated_by"
                        " FROM equipment_property_values WHERE equipment_id = %s ORDER BY property_id",
                        (node["id"],)))


@pytest.fixture
def engineer(at_unit):
    """An engineer holding the node's unit."""
    return at_unit("maint_engineer")


@pytest.fixture
def make_property(admin):
    """make_property("A power") -> a number property in kW named "<prefix> <n>"; data_type= etc."""
    def make(prefix, **overrides):
        body = {"name": f"{prefix} {next(_numbers):04d}", "data_type": "number", "unit": "kW", **overrides}
        if body["data_type"] != "number":
            body.pop("unit")
        return _ok(admin.post(f"{MASTERS}/properties", json=body), 201)
    return make


@pytest.fixture
def link(admin):
    def add(class_id, *props):
        _ok(admin.post(f"{MASTERS}/equipment-classes/{class_id}/properties",
                       json={"property_ids": [p["id"] for p in props]}))
    return add


def _set_model(admin, model_id, values):
    _ok(admin.put(f"{MASTERS}/equipment-models/{model_id}/properties",
                  json={"values": {str(p["id"]): v for p, v in values}}))


@pytest.fixture
def props(make_property):
    """One property of each data type; the names sort A, B, C, D."""
    return {
        "power": make_property("A rated power"),
        "orientation": make_property("B shaft orientation", data_type="choice", options=["Horizontal", "Vertical"]),
        "frame": make_property("C frame size", data_type="text"),
        "exproof": make_property("D ex-proof", data_type="yes_no"),
    }


@pytest.fixture
def motor(admin, node, props, link):
    """The node, its class holding the four properties, its model giving the power 7.5 kW."""
    link(node["class_id"], *props.values())
    _set_model(admin, node["model_id"], [(props["power"], "7.5")])
    return node


@pytest.fixture
def no_model_part(admin, motor):
    """A component-unit with no model (S033) under the motor, of the motor's class."""
    return _ok(admin.post(EQUIPMENT, json={"level": "component_unit", "parent_id": motor["id"], "model_id": None,
                                           "class_id": motor["class_id"], "name": "Rewound motor"}), 201)


def _key(prop):
    return str(prop["id"])


class TestRead:

    def test_an_item_with_a_model_and_no_own_values(self, engineer, motor, props):
        items = _made(_ok(engineer.get(_url(motor)))["items"], *props.values())
        assert [i["property_id"] for i in items] == [props[k]["id"] for k in ("power", "orientation", "frame",
                                                                               "exproof")]
        power, orientation = items[0], items[1]
        assert power == {"property_id": props["power"]["id"], "name": props["power"]["name"], "data_type": "number",
                         "unit": "kW", "options": [], "value": None, "model_display": "7.5 kW", "has_model": True,
                         "per_item_only": False}
        assert [o["label"] for o in orientation["options"]] == ["Horizontal", "Vertical"]
        assert (orientation["value"], orientation["model_display"]) == (None, None)

    def test_an_item_with_own_values(self, engineer, motor, props):
        horizontal = props["orientation"]["options"][0]["id"]
        _ok(engineer.put(_url(motor), json={"values": {_key(props["power"]): "5.5",
                                                       _key(props["orientation"]): horizontal}}))
        items = {i["property_id"]: i for i in _ok(engineer.get(_url(motor)))["items"]}
        assert (items[props["power"]["id"]]["value"], items[props["power"]["id"]]["model_display"]) == ("5.5", "7.5 kW")
        assert items[props["orientation"]["id"]]["value"] == horizontal

    def test_a_model_less_component_unit(self, engineer, no_model_part):
        items = _ok(engineer.get(_url(no_model_part)))["items"]
        assert len(items) == 4
        assert all(not i["has_model"] and i["model_display"] is None and i["value"] is None for i in items)

    def test_a_scrapped_item_is_readable(self, admin, engineer, motor, props):
        _ok(admin.put(f"{EQUIPMENT}/{motor['id']}", json={"lifecycle": "scrapped"}))
        assert len(_made(_ok(engineer.get(_url(motor)))["items"], *props.values())) == 4


class TestWrite:

    def test_set_change_and_clear_each_with_its_event(self, engineer, admin, motor, props, db_rows):
        power = props["power"]
        name = power["name"]
        items = _ok(engineer.put(_url(motor), json={"values": {_key(power): "5.5"}}))["items"]
        assert items[0]["value"] == "5.5"
        assert _card(admin, motor)[name] == ("5.5 kW", "item")
        rows = _own_rows(db_rows, motor)
        assert [(r["property_id"], str(r["value_number"]), r["updated_at"] is not None) for r in rows] == [
            (power["id"], "5.5000", True)]
        assert rows[0]["updated_by"].startswith("user")   # the engineer's username (at_unit)
        _ok(engineer.put(_url(motor), json={"values": {_key(power): "6"}}))
        _ok(engineer.put(_url(motor), json={"values": {_key(power): ""}}))
        assert _own_rows(db_rows, motor) == []
        assert _card(admin, motor)[name] == ("7.5 kW", "model")
        assert _events(admin, motor) == [
            (f"{name}: 7.5 kW (model)", f"{name}: 5.5 kW"),
            (f"{name}: 5.5 kW", f"{name}: 6 kW"),
            (f"{name}: 6 kW", f"{name}: 7.5 kW (model)"),
        ]

    def test_a_value_equal_to_the_model_s_is_stored_as_the_item_s_own(self, engineer, admin, motor, props, db_rows):
        _ok(engineer.put(_url(motor), json={"values": {_key(props["power"]): "7.50"}}))
        assert len(_own_rows(db_rows, motor)) == 1
        name = props["power"]["name"]
        assert _card(admin, motor)[name] == ("7.5 kW", "item")
        assert _events(admin, motor) == [(f"{name}: 7.5 kW (model)", f"{name}: 7.5 kW")]

    def test_a_full_body_with_one_change_writes_one_row_and_one_event(self, engineer, admin, motor, props, db_rows):
        _ok(engineer.put(_url(motor), json={"values": {_key(props["exproof"]): True}}))
        # The dialog sends every row: the unchanged own value and three empty ones
        values = {_key(props["power"]): "", _key(props["orientation"]): "", _key(props["frame"]): " 132M ",
                  _key(props["exproof"]): True}
        _ok(engineer.put(_url(motor), json={"values": values}))
        assert [r["property_id"] for r in _own_rows(db_rows, motor)] == sorted([props["frame"]["id"],
                                                                                props["exproof"]["id"]])
        frame, exproof = props["frame"]["name"], props["exproof"]["name"]
        assert _events(admin, motor) == [
            (f"{exproof}: no value (model)", f"{exproof}: Yes"),
            (f"{frame}: no value (model)", f"{frame}: 132M"),
        ]

    def test_a_clear_of_a_row_with_no_own_value_writes_nothing(self, engineer, admin, motor, props, db_rows):
        _ok(engineer.put(_url(motor), json={"values": {_key(props["power"]): None, _key(props["frame"]): ""}}))
        assert (_own_rows(db_rows, motor), _events(admin, motor)) == ([], [])

    def test_an_option_label_in_the_history(self, engineer, admin, motor, props):
        horizontal, vertical = (o["id"] for o in props["orientation"]["options"])
        _ok(engineer.put(_url(motor), json={"values": {_key(props["orientation"]): horizontal}}))
        _ok(engineer.put(_url(motor), json={"values": {_key(props["orientation"]): vertical}}))
        name = props["orientation"]["name"]
        assert _events(admin, motor) == [(f"{name}: no value (model)", f"{name}: Horizontal"),
                                         (f"{name}: Horizontal", f"{name}: Vertical")]

    def test_a_model_less_item_holds_only_its_own(self, engineer, admin, no_model_part, props):
        _ok(engineer.put(_url(no_model_part), json={"values": {_key(props["frame"]): "132M"}}))
        frame = props["frame"]["name"]
        assert _card(admin, no_model_part)[frame] == ("132M", "item")
        assert _card(admin, no_model_part)[props["power"]["name"]] == (None, None)
        _ok(engineer.put(_url(no_model_part), json={"values": {_key(props["frame"]): None}}))
        assert _events(admin, no_model_part) == [(f"{frame}: no value", f"{frame}: 132M"),
                                                 (f"{frame}: 132M", f"{frame}: no value")]

    def test_an_inactive_stored_option_is_kept(self, engineer, admin, motor, props):
        horizontal = props["orientation"]["options"][0]["id"]
        _ok(engineer.put(_url(motor), json={"values": {_key(props["orientation"]): horizontal}}))
        _ok(admin.put(f"{MASTERS}/property-options/{horizontal}", json={"active": False}))
        items = _ok(engineer.put(_url(motor), json={"values": {_key(props["orientation"]): horizontal}}))["items"]
        assert [o["label"] for o in items[1]["options"]] == ["Horizontal", "Vertical"]
        assert len(_events(admin, motor)) == 1

    def test_an_empty_values_object_saves_nothing(self, engineer, motor, props):
        assert len(_made(_ok(engineer.put(_url(motor), json={"values": {}}))["items"], *props.values())) == 4


class TestRefusals:

    def test_values_shape(self, engineer, motor):
        for body in ({}, {"values": []}, {"values": "x"}):
            assert _refusal(engineer.put(_url(motor), json=body)) == (400, "values", VALUES_NOT_OBJECT)
        assert _refusal(engineer.put(_url(motor), json={"values": {"abc": 1}})) == (400, "values.abc", NOT_ON_CLASS)

    def test_not_on_the_class_unlinked_inactive_or_unknown(self, engineer, admin, motor, props, make_property, db_rows):
        stranger = make_property("E stranger")
        _ok(admin.put(f"{MASTERS}/properties/{props['frame']['id']}", json={"active": False}))
        for key in (_key(stranger), _key(props["frame"]), "999999999"):
            assert _refusal(engineer.put(_url(motor), json={"values": {key: "1"}})) == (400, f"values.{key}",
                                                                                      NOT_ON_CLASS)
        assert _own_rows(db_rows, motor) == []

    def test_the_first_refusal_by_name_answers_and_nothing_is_saved(self, engineer, admin, motor, props, db_rows):
        values = {_key(props["exproof"]): "yes", _key(props["power"]): "abc", _key(props["frame"]): "kept?"}
        assert _refusal(engineer.put(_url(motor), json={"values": values})) == (
            400, f"values.{props['power']['id']}", ENTER_NUMBER)
        assert (_own_rows(db_rows, motor), _events(admin, motor)) == ([], [])

    @pytest.mark.parametrize("prop, raw, message", [
        ("power", "1.00001", TOO_MANY_DECIMALS),
        ("power", "abc", ENTER_NUMBER),
        ("frame", "x" * 101, TEXT_TOO_LONG),
        ("exproof", "yes", CHOOSE_YES_NO),
        ("orientation", 999999999, CHOOSE_OPTION),
    ])
    def test_each_data_type_s_bad_value(self, engineer, motor, props, prop, raw, message):
        res = engineer.put(_url(motor), json={"values": {_key(props[prop]): raw}})
        assert _refusal(res) == (400, f"values.{props[prop]['id']}", message)

    def test_a_scrapped_item_is_409(self, engineer, admin, motor, props, db_rows):
        _ok(admin.put(f"{EQUIPMENT}/{motor['id']}", json={"lifecycle": "scrapped"}))
        assert _refusal(engineer.put(_url(motor), json={"values": {_key(props["power"]): "5.5"}})) == (
            409, None, SCRAPPED)
        assert _own_rows(db_rows, motor) == []

    def test_another_site_s_engineer_reads_but_is_403(self, user_at_sites, make_site, make_unit, make_equipment,
                                                      props, link, db_rows):
        site_a, site_b = make_site(), make_site()
        unit_a = make_unit(site_a)
        node = make_equipment(unit=unit_a)
        link(node["class_id"], props["power"])
        client, _ = user_at_sites([(site_a, "maint_operator", [unit_a]), (site_b, "maint_engineer", "all")])
        assert client.get(_url(node)).status_code == 200
        assert client.put(_url(node), json={"values": {_key(props["power"]): "5.5"}}).status_code == 403
        assert _own_rows(db_rows, node) == []

    def test_an_operator_cannot_write(self, at_unit, motor, props):
        res = at_unit("maint_operator").put(_url(motor), json={"values": {_key(props["power"]): "5.5"}})
        assert res.status_code == 403

    def test_an_unseen_or_unknown_node_is_404(self, user_with_units, make_unit, engineer, motor, props):
        outsider = user_with_units("maint_engineer", [make_unit()])
        assert outsider.get(_url(motor)).status_code == 404
        assert outsider.put(_url(motor), json={"values": {_key(props["power"]): "5.5"}}).status_code == 404
        assert engineer.get(f"{EQUIPMENT}/999999999/properties").status_code == 404
        assert engineer.put(f"{EQUIPMENT}/999999999/properties", json={"values": {}}).status_code == 404


class TestModelAndClassChanges:

    def test_a_new_model_of_the_same_class_keeps_the_own_values(self, engineer, admin, motor, props, make_model):
        _ok(engineer.put(_url(motor), json={"values": {_key(props["power"]): "5.5"}}))
        other = make_model(cls={"id": motor["class_id"]})
        _set_model(admin, other["id"], [(props["power"], "11")])
        _ok(admin.put(f"{EQUIPMENT}/{motor['id']}", json={"model_id": other["id"]}))
        power = _ok(engineer.get(_url(motor)))["items"][0]
        assert (power["value"], power["model_display"]) == ("5.5", "11 kW")
        assert _card(admin, motor)[props["power"]["name"]] == ("5.5 kW", "item")

    def test_clearing_a_component_unit_s_model_keeps_the_own_values(self, engineer, admin, motor, props,
                                                                    make_equipment, make_model):
        part = make_equipment(parent=motor, model=make_model(cls={"id": motor["class_id"]}))
        _ok(engineer.put(_url(part), json={"values": {_key(props["frame"]): "132M"}}))
        _ok(admin.put(f"{EQUIPMENT}/{part['id']}", json={"model_id": None, "class_id": motor["class_id"]}))
        frame = next(i for i in _ok(engineer.get(_url(part)))["items"] if i["property_id"] == props["frame"]["id"])
        assert (frame["value"], frame["has_model"]) == ("132M", False)

    def test_a_class_change_hides_and_linking_again_shows(self, engineer, admin, no_model_part, props, make_class,
                                                          link, db_rows):
        _ok(engineer.put(_url(no_model_part), json={"values": {_key(props["frame"]): "132M",
                                                               _key(props["power"]): "5.5"}}))
        other = make_class()
        link(other["id"], props["power"])
        _ok(admin.put(f"{EQUIPMENT}/{no_model_part['id']}", json={"class_id": other["id"], "type_id": None}))
        assert [i["property_id"] for i in _ok(engineer.get(_url(no_model_part)))["items"]] == [props["power"]["id"]]
        assert _card(admin, no_model_part) == {props["power"]["name"]: ("5.5 kW", "item")}
        assert len(_own_rows(db_rows, no_model_part)) == 2   # hidden, not deleted
        link(other["id"], props["frame"])
        assert _card(admin, no_model_part)[props["frame"]["name"]] == ("132M", "item")

    def test_a_model_of_another_class_keeps_and_hides(self, engineer, admin, motor, props, make_class, make_model,
                                                      link, db_rows):
        _ok(engineer.put(_url(motor), json={"values": {_key(props["power"]): "5.5", _key(props["frame"]): "132M"}}))
        other = make_class()
        link(other["id"], props["power"])
        model = make_model(cls=other)
        _ok(admin.put(f"{EQUIPMENT}/{motor['id']}", json={"model_id": model["id"]}))
        rows = _made(_ok(admin.get(f"{EQUIPMENT}/{motor['id']}"))["properties"], *props.values())
        assert [(r["name"], r["display"], r["source"]) for r in rows] == [(props["power"]["name"], "5.5 kW", "item")]
        assert len(_own_rows(db_rows, motor)) == 2


class TestDatabaseDown:

    def test_a_read_and_a_write_are_503(self, admin, db_down):
        assert admin.get(f"{EQUIPMENT}/1/properties").status_code == 503
        assert admin.put(f"{EQUIPMENT}/1/properties", json={"values": {}}).status_code == 503


# ---------------------------------------------------------------------------
# S061: every-class properties, per-machine values, Location (§ 5, § 8.2)
# ---------------------------------------------------------------------------

GPS = "GPS location"


def _gps(admin):
    """The seed "GPS location" (migration v34)."""
    return next(p for p in _ok(admin.get(f"{MASTERS}/properties"))["items"] if p["name"] == GPS)


def _card_row(admin, node, prop):
    return next((p for p in _ok(admin.get(f"{EQUIPMENT}/{node['id']}"))["properties"]
                 if p["property_id"] == prop["id"]), None)


@pytest.fixture
def every_class(admin, make_property):
    """A Yes / No property on every class; the flag is turned off afterwards, so it does not show
    on the later tests' machines."""
    made = []

    def make(prefix, **overrides):
        prop = make_property(prefix, data_type="yes_no", all_classes=True, **overrides)
        made.append(prop)
        return prop
    yield make
    for prop in made:
        _ok(admin.put(f"{MASTERS}/properties/{prop['id']}", json={"all_classes": False}))


class TestEveryClass:

    def test_shown_and_saved_on_an_unlinked_class_and_hidden_when_turned_off(self, engineer, admin, node,
                                                                             every_class, db_rows):
        prop = every_class("S061 every")
        assert _card_row(admin, node, prop)["display"] is None
        assert prop["id"] in [i["property_id"] for i in _ok(engineer.get(_url(node)))["items"]]
        _ok(engineer.put(_url(node), json={"values": {_key(prop): True}}))
        assert _card_row(admin, node, prop)["display"] == "Yes"
        _ok(admin.put(f"{MASTERS}/properties/{prop['id']}", json={"all_classes": False}))
        assert _card_row(admin, node, prop) is None
        assert _refusal(engineer.put(_url(node), json={"values": {_key(prop): False}})) == (
            400, f"values.{prop['id']}", NOT_ON_CLASS)
        # The value stays, hidden, as with Remove from a class
        assert [r["value_bool"] for r in _own_rows(db_rows, node) if r["property_id"] == prop["id"]] == [1]


class TestLocation:

    def test_set_with_its_event_card_display_and_map_link(self, engineer, admin, node, db_rows):
        gps = _gps(admin)
        items = _ok(engineer.put(_url(node), json={"values": {_key(gps): "11.0168234567, 76.9558123"}}))["items"]
        row = next(i for i in items if i["property_id"] == gps["id"])
        assert (row["data_type"], row["value"], row["per_item_only"], row["model_display"]) == (
            "geo", "11.016823, 76.955812", True, None)
        card = _card_row(admin, node, gps)
        assert (card["display"], card["source"], card["map_url"]) == (
            "11.016823, 76.955812", "item",
            "https://www.google.com/maps/search/?api=1&query=11.016823,76.955812")
        stored = db_rows("SELECT value_lat, value_lng, value_number, value_text FROM equipment_property_values"
                         " WHERE equipment_id = %s AND property_id = %s", (node["id"], gps["id"]))
        assert [(str(r["value_lat"]), str(r["value_lng"]), r["value_number"], r["value_text"]) for r in stored] == [
            ("11.016823", "76.955812", None, None)]
        # A per-machine property has no model value: no "(model)" mark (§ 5.6)
        assert _events(admin, node) == [(f"{GPS}: no value", f"{GPS}: 11.016823, 76.955812")]

    def test_a_re_save_with_the_same_location_writes_nothing(self, engineer, admin, node, db_rows):
        """BR1-05: the pattern of test_a_clear_of_a_row_with_no_own_value_writes_nothing."""
        gps = _gps(admin)
        _ok(engineer.put(_url(node), json={"values": {_key(gps): "11.016823, 76.955812"}}))
        before = _own_rows(db_rows, node)
        _ok(engineer.put(_url(node), json={"values": {_key(gps): "11.0168230 76.955812"}}))
        assert _own_rows(db_rows, node) == before
        assert len(_events(admin, node)) == 1

    @pytest.mark.parametrize("raw, message", [
        ("95, 76", "The latitude must be between -90 and 90"),
        ("11, 200", "The longitude must be between -180 and 180"),
        ("11.016823", "Enter the location as latitude, longitude, for example 11.016823, 76.955812"),
    ])
    def test_a_bad_location_is_400_on_its_field(self, engineer, admin, node, raw, message):
        gps = _gps(admin)
        assert _refusal(engineer.put(_url(node), json={"values": {_key(gps): raw}})) == (
            400, f"values.{gps['id']}", message)

    def test_a_component_unit_has_no_location(self, engineer, admin, no_model_part):
        gps = _gps(admin)
        assert gps["id"] not in [p["property_id"] for p in _ok(admin.get(f"{EQUIPMENT}/{no_model_part['id']}"))[
            "properties"]]
        assert gps["id"] not in [i["property_id"] for i in _ok(engineer.get(_url(no_model_part)))["items"]]
        assert _refusal(engineer.put(_url(no_model_part), json={"values": {_key(gps): "11, 76"}})) == (
            400, f"values.{gps['id']}", NOT_ON_CLASS)

    def test_an_operator_cannot_set_it(self, at_unit, admin, node):
        gps = _gps(admin)
        assert at_unit("maint_operator").put(_url(node), json={"values": {_key(gps): "11, 76"}}).status_code == 403


class TestMovingHint:

    def test_portable_shows_the_hint_and_fixed_does_not(self, engineer, admin, node, link):
        gps = _gps(admin)
        mobility = _ok(admin.post(f"{MASTERS}/properties", json={
            "name": "Mobility", "data_type": "choice", "options": ["Fixed", "Mobile", "Portable"]}), 201)
        try:
            link(node["class_id"], mobility)
            fixed, _, portable = (o["id"] for o in mobility["options"])
            _ok(engineer.put(_url(node), json={"values": {_key(gps): "11.016823, 76.955812",
                                                          _key(mobility): portable}}))
            assert _ok(admin.get(f"{EQUIPMENT}/{node['id']}"))["moving_hint"] == (
                "This machine moves. The location may be out of date.")
            _ok(engineer.put(_url(node), json={"values": {_key(mobility): fixed}}))
            assert _ok(admin.get(f"{EQUIPMENT}/{node['id']}"))["moving_hint"] is None
        finally:
            # The name is unique: rename it, so no later test meets a "Mobility"
            _ok(admin.put(f"{MASTERS}/properties/{mobility['id']}", json={"name": f"Mobility done {node['id']}"}))
