"""A node's meters (S038 § 1.2, § 1.3, § 5): its model's plus its own, overrides, history, against
the test DB.  Needs the dev MariaDB container (tooling/dev/dev-db-up.bat).  Every test makes its
own meter types, models and nodes.
"""

import pytest

from tests.pm_helpers import attach, make_template

EQUIPMENT = "/api/equipment"
MASTERS = "/api/masters"
SCRAPPED = "This record is scrapped and cannot be changed"


def _url(node, meter_type=None):
    base = f"{EQUIPMENT}/{node['id']}/meters"
    return base if meter_type is None else f"{base}/{meter_type['id']}"


def _ok(res, status=200):
    assert res.status_code == status, res.get_json()
    return res.get_json()


def _refusal(res):
    body = res.get_json()
    return res.status_code, body.get("field"), body["error"]


def _by_type(meters):
    return {m["meter_type"]["id"]: m for m in meters}


def _model_meter(client, model_id, meter_type, **limits):
    return _ok(client.post(f"{MASTERS}/equipment-models/{model_id}/meters",
                           json={"meter_type_id": meter_type["id"], **limits}), 201)


def _events(admin, node):
    """The node's meter history lines, oldest first."""
    events = _ok(admin.get(f"{EQUIPMENT}/{node['id']}"))["events"]
    return [(e["event"], e["old_value"], e["new_value"]) for e in reversed(events) if e["event"].startswith("meter_")]


def _node_rows(db_rows, node):
    return list(db_rows("SELECT meter_type_id, own, min_value, max_value, active FROM node_meters"
                        " WHERE equipment_id = %s ORDER BY meter_type_id", (node["id"],)))


@pytest.fixture
def engineer(at_unit):
    return at_unit("maint_engineer")


@pytest.fixture
def oil(make_meter_type):
    return make_meter_type()


@pytest.fixture
def press(admin, node, oil):
    """The node with one model meter: oil temperature, 10–60 °C."""
    _model_meter(admin, node["model_id"], oil, min_value="10", max_value="60")
    return node


class TestList:

    def test_model_meters_own_meters_and_an_override(self, engineer, press, oil, make_meter_type):
        hours = make_meter_type(kind="counter", unit="h")
        _ok(engineer.post(_url(press), json={"meter_type_id": hours["id"]}), 201)
        _ok(engineer.put(_url(press, oil), json={"max_value": "55"}))
        meters = _by_type(_ok(engineer.get(_url(press))))
        assert meters[oil["id"]] == {
            "meter_type": {"id": oil["id"], "name": oil["name"], "unit": "°C", "kind": "gauge", "decimals": 1,
                           "expected_answer": None},
            "source": "model", "min_value": "10", "max_value": "55", "model_min": "10", "model_max": "60",
            "overridden": True, "limits_text": "Limits: 10–55 °C", "model_limits_text": "Limits: 10–60 °C",
            "last": None,   # no reading yet (S039)
            "linked_by": []}   # no part uses it through a meter link (S104 A1)
        assert (meters[hours["id"]]["source"], meters[hours["id"]]["limits_text"]) == ("node", None)

    def test_a_yes_no_meter_carries_its_expected_answer(self, engineer, admin, node, make_meter_type):
        question = make_meter_type(kind="yes_no", expected_answer="no")
        _model_meter(admin, node["model_id"], question)
        meter = _ok(engineer.get(_url(node)))[0]
        assert (meter["meter_type"]["expected_answer"], meter["limits_text"]) == ("no", None)

    def test_meters_added_to_an_inactive_model_show_on_its_machines(self, engineer, admin, node, oil):
        _ok(admin.put(f"{MASTERS}/equipment-models/{node['model_id']}", json={"active": False}))
        _model_meter(admin, node["model_id"], oil)
        assert list(_by_type(_ok(engineer.get(_url(node))))) == [oil["id"]]

    def test_a_model_change_changes_the_list_and_an_override_comes_back(self, admin, press, oil, make_model):
        _ok(admin.put(_url(press, oil), json={"max_value": "55"}))
        old_model = press["model_id"]
        _ok(admin.put(f"{EQUIPMENT}/{press['id']}", json={"model_id": make_model()["id"]}))
        assert _ok(admin.get(_url(press))) == []
        _ok(admin.put(f"{EQUIPMENT}/{press['id']}", json={"model_id": old_model}))
        meter = _ok(admin.get(_url(press)))[0]
        assert (meter["max_value"], meter["overridden"]) == ("55", True)

    def test_a_component_unit_without_a_model_has_only_its_own(self, admin, node, make_class, make_meter_type):
        pump = _ok(admin.post(EQUIPMENT, json={"level": "component_unit", "parent_id": node["id"], "model_id": None,
                                               "class_id": make_class()["id"], "name": "Pump A"}), 201)
        assert _ok(admin.get(_url(pump))) == []
        hours = make_meter_type(kind="counter", unit="h")
        meters = _ok(admin.post(_url(pump), json={"meter_type_id": hours["id"]}), 201)
        assert [(m["meter_type"]["id"], m["source"]) for m in meters] == [(hours["id"], "node")]

    def test_a_storekeeper_reads_at_their_unit_and_an_outsider_gets_404(self, at_unit, user_with_units,
                                                                         make_unit, press):
        assert len(_ok(at_unit("maint_storekeeper").get(_url(press)))) == 1
        assert user_with_units("maint_engineer", [make_unit()]).get(_url(press)).status_code == 404


class TestAddOwn:

    def test_add_an_own_gauge_with_limits_and_its_history(self, engineer, admin, node, make_meter_type):
        fuel = make_meter_type(unit="%", decimals=0)
        meters = _ok(engineer.post(_url(node), json={"meter_type_id": fuel["id"], "min_value": "10"}), 201)
        assert [(m["source"], m["limits_text"]) for m in meters] == [("node", "Limits: from 10 %")]
        assert _events(admin, node) == [("meter_added", None, fuel["name"])]

    def test_a_meter_already_in_force_is_409_and_writes_no_history(self, engineer, admin, press, oil,
                                                                   make_meter_type):
        assert _refusal(engineer.post(_url(press), json={"meter_type_id": oil["id"]})) == (
            409, "meter_type_id", "This machine already has this meter")
        fuel = make_meter_type()
        _ok(engineer.post(_url(press), json={"meter_type_id": fuel["id"]}), 201)
        assert _refusal(engineer.post(_url(press), json={"meter_type_id": fuel["id"]}))[0] == 409
        assert _events(admin, press) == [("meter_added", None, fuel["name"])]

    def test_refusals(self, engineer, admin, node, make_meter_type):
        assert _refusal(engineer.post(_url(node), json={})) == (400, "meter_type_id", "Pick a meter type")
        inactive = make_meter_type()
        admin.put(f"{MASTERS}/meter-types/{inactive['id']}", json={"active": False})
        assert _refusal(engineer.post(_url(node), json={"meter_type_id": inactive["id"]})) == (
            409, "meter_type_id", "This meter type is inactive. Pick another meter type.")
        counter = make_meter_type(kind="counter", unit="h")
        assert _refusal(engineer.post(_url(node), json={"meter_type_id": counter["id"], "max_value": "5"})) == (
            400, "max_value", "A counter has no limits")
        assert _events(admin, node) == []

    def test_remove_clears_the_limits_and_a_new_add_brings_the_row_back(self, engineer, admin, db_rows, node,
                                                                         make_meter_type):
        fuel = make_meter_type()
        _ok(engineer.post(_url(node), json={"meter_type_id": fuel["id"], "max_value": "90"}), 201)
        assert _ok(engineer.put(_url(node, fuel), json={"active": False})) == []
        assert [(r["own"], r["min_value"], r["max_value"], r["active"]) for r in _node_rows(db_rows, node)] == [
            (1, None, None, 0)]
        meters = _ok(engineer.post(_url(node), json={"meter_type_id": fuel["id"]}), 201)
        assert [m["limits_text"] for m in meters] == ["No limits"]
        assert len(_node_rows(db_rows, node)) == 1
        assert [e[0] for e in _events(admin, node)] == ["meter_added", "meter_removed", "meter_added"]
        assert _events(admin, node)[1] == ("meter_removed", fuel["name"], None)

    def test_an_own_meter_replaces_a_stale_override(self, admin, db_rows, press, oil, make_model):
        _ok(admin.put(_url(press, oil), json={"max_value": "55"}))
        _ok(admin.put(f"{EQUIPMENT}/{press['id']}", json={"model_id": make_model()["id"]}))
        meters = _ok(admin.post(_url(press), json={"meter_type_id": oil["id"], "min_value": "5"}), 201)
        assert [(m["source"], m["min_value"], m["max_value"]) for m in meters] == [("node", "5", None)]
        assert [(r["own"], r["active"]) for r in _node_rows(db_rows, press)] == [(1, 1)]


class TestOverride:

    def test_set_and_clear_an_override_with_both_sides_in_history(self, engineer, admin, db_rows, press, oil):
        meters = _ok(engineer.put(_url(press, oil), json={"min_value": None, "max_value": "55"}))
        assert (meters[0]["limits_text"], meters[0]["overridden"]) == ("Limits: up to 55 °C", True)
        assert [r["own"] for r in _node_rows(db_rows, press)] == [0]
        meters = _ok(engineer.put(_url(press, oil), json={"use_model_limits": True}))
        assert (meters[0]["limits_text"], meters[0]["overridden"]) == ("Limits: 10–60 °C", False)
        assert _node_rows(db_rows, press) == []
        name = oil["name"]
        assert _events(admin, press) == [
            ("meter_limits", f"{name}: 10–60 °C", f"{name}: up to 55 °C"),
            ("meter_limits", f"{name}: up to 55 °C", f"{name}: 10–60 °C")]

    def test_a_one_sided_update_starts_from_the_model_s_limits(self, engineer, press, oil):
        meters = _ok(engineer.put(_url(press, oil), json={"max_value": "50"}))
        assert (meters[0]["min_value"], meters[0]["max_value"]) == ("10", "50")
        assert _refusal(engineer.put(_url(press, oil), json={"min_value": "51"})) == (
            400, "max_value", "Min must not be above Max")

    def test_an_override_equal_to_the_model_leaves_no_row(self, engineer, admin, db_rows, press, oil):
        meters = _ok(engineer.put(_url(press, oil), json={"min_value": "10.0", "max_value": 60}))
        assert meters[0]["overridden"] is False
        assert _node_rows(db_rows, press) == []
        assert _events(admin, press) == []

    def test_an_own_row_the_model_gains_later_keeps_its_place(self, engineer, admin, db_rows, node, oil):
        _ok(engineer.post(_url(node), json={"meter_type_id": oil["id"], "max_value": "50"}), 201)
        _model_meter(admin, node["model_id"], oil, min_value="10", max_value="60")
        meter = _ok(engineer.get(_url(node)))[0]
        assert (meter["source"], meter["max_value"], meter["overridden"]) == ("model", "50", True)
        # Use the model's limits: the own row stays, with no limits
        meter = _ok(engineer.put(_url(node, oil), json={"use_model_limits": True}))[0]
        assert (meter["limits_text"], meter["overridden"]) == ("Limits: 10–60 °C", False)
        assert [(r["own"], r["min_value"], r["max_value"], r["active"]) for r in _node_rows(db_rows, node)] == [
            (1, None, None, 1)]
        # An override equal to the model on that own row: NULLs, row kept
        _ok(engineer.put(_url(node, oil), json={"max_value": "45"}))
        _ok(engineer.put(_url(node, oil), json={"max_value": "60"}))
        assert [(r["own"], r["min_value"], r["max_value"]) for r in _node_rows(db_rows, node)] == [(1, None, None)]

    def test_set_limits_over_a_removed_own_row_writes_it_and_leaves_it_inactive(self, engineer, admin, db_rows,
                                                                               node, oil, make_model):
        _ok(engineer.post(_url(node), json={"meter_type_id": oil["id"]}), 201)
        _ok(engineer.put(_url(node, oil), json={"active": False}))
        _model_meter(admin, node["model_id"], oil, min_value="10", max_value="60")
        meter = _ok(engineer.put(_url(node, oil), json={"max_value": "40"}))[0]
        assert (meter["max_value"], meter["overridden"]) == ("40", True)
        rows = _node_rows(db_rows, node)
        assert [(r["own"], r["max_value"], r["active"]) for r in rows] == [(1, 40, 0)]
        # A later model change: the removed own meter stays removed
        _ok(admin.put(f"{EQUIPMENT}/{node['id']}", json={"model_id": make_model()["id"]}))
        assert _ok(engineer.get(_url(node))) == []

    def test_limits_on_a_meter_no_longer_on_the_model_are_409(self, engineer, admin, press, oil):
        row = _ok(admin.get(f"{MASTERS}/equipment-models/{press['model_id']}/meters"))[0]
        _ok(admin.put(f"{MASTERS}/model-meters/{row['id']}", json={"active": False}))
        for body in ({"max_value": "50"}, {"use_model_limits": True}):
            assert _refusal(engineer.put(_url(press, oil), json=body)) == (
                409, None, "This meter is no longer on the model. Reload the page.")

    def test_a_model_meter_cannot_be_removed_on_one_node(self, engineer, admin, press, oil):
        status, _, message = _refusal(engineer.put(_url(press, oil), json={"active": False}))
        model = _ok(admin.get(f"{EQUIPMENT}/{press['id']}"))
        assert (status, message) == (
            409, f"Comes from the model {model['model_label']}. Remove it in Masters › Models, "
                 "or change this machine's model.")
        assert _events(admin, press) == []


class TestWhoAndWhen:

    def test_another_site_s_engineer_is_403(self, user_at_sites, make_site, make_unit, make_equipment, admin, oil):
        site_a, site_b = make_site(), make_site()
        unit_a = make_unit(site_a)
        node = make_equipment(unit=unit_a)
        client, _ = user_at_sites([(site_a, "maint_operator", [unit_a]), (site_b, "maint_engineer", "all")])
        assert client.get(_url(node)).status_code == 200
        assert client.post(_url(node), json={"meter_type_id": oil["id"]}).status_code == 403
        assert client.put(_url(node, oil), json={"max_value": "5"}).status_code == 403
        assert _events(admin, node) == []

    def test_an_operator_cannot_write(self, at_unit, node, oil):
        assert at_unit("maint_operator").post(_url(node), json={"meter_type_id": oil["id"]}).status_code == 403

    def test_a_scrapped_node_is_read_only(self, engineer, admin, press, oil, make_meter_type):
        _ok(admin.put(f"{EQUIPMENT}/{press['id']}", json={"lifecycle": "scrapped"}))
        fuel = make_meter_type()
        for res in (engineer.post(_url(press), json={"meter_type_id": fuel["id"]}),
                    engineer.put(_url(press, oil), json={"max_value": "5"})):
            assert _refusal(res) == (409, None, SCRAPPED)
        assert len(_ok(engineer.get(_url(press)))) == 1

    def test_unknown_node_and_unknown_meter(self, engineer, node, make_meter_type):
        assert engineer.get(f"{EQUIPMENT}/99999999/meters").status_code == 404
        assert engineer.put(f"{EQUIPMENT}/{node['id']}/meters/99999999", json={"active": False}).status_code == 404
        assert engineer.put(_url(node, make_meter_type()), json={"active": False}).status_code == 404


# ---------------------------------------------------------------------------
# Meter links (S104 A1.6.1, A1.6.5, A1.7, A1.9)
# ---------------------------------------------------------------------------

def _links(node):
    return f"{EQUIPMENT}/{node['id']}/meter-links"


def _link(client, part, source, meter_type):
    return client.post(_links(part), json={"meter_type_id": meter_type["id"], "source_equipment_id": source["id"]})


def _linked(meters):
    return {m["meter_type"]["id"]: m for m in meters if m["source"] == "linked"}


def _read(client, node, meter_type, value):
    return _ok(client.post(f"{EQUIPMENT}/{node['id']}/readings", json={"meter_type_id": meter_type["id"],
                                                                      "value": value}), 201)


@pytest.fixture
def hours(make_meter_type):
    return make_meter_type(kind="counter", unit="h", decimals=0)


@pytest.fixture
def tree(admin, press, hours, make_equipment):
    """The press (model meters: oil 10–60 °C and run hours), a component unit under it with a component, and a
    component right under the press -> {press, unit_node, part (under the unit), comp (under the press)}."""
    _model_meter(admin, press["model_id"], hours)
    unit_node = make_equipment(parent=press)
    return {"press": press, "unit_node": unit_node, "part": make_equipment(parent=unit_node, level="component"),
            "comp": make_equipment(parent=press, level="component")}


class TestMeterLinks:

    def test_a_component_links_the_press_s_meter(self, engineer, admin, tree, oil, at_unit):
        press, comp = tree["press"], tree["comp"]
        meters = _ok(_link(engineer, comp, press, oil), 201)
        (entry,) = _linked(meters).values()
        assert entry == {
            "meter_type": {"id": oil["id"], "name": oil["name"], "unit": "°C", "kind": "gauge", "decimals": 1,
                           "expected_answer": None},
            "source": "linked", "linked_from": {"id": press["id"], "code": press["code"], "name": press["name"]},
            "in_use": True, "not_in_use": None, "min_value": "10", "max_value": "60",
            "limits_text": "Limits: 10–60 °C", "model_min": None, "model_max": None, "model_limits_text": None,
            "overridden": False, "last": None, "used_by": [], "linked_by": []}
        assert _events(admin, comp) == [("meter_linked", None, f"{oil['name']} from {press['code']}")]
        _read(at_unit("maint_operator"), press, oil, "45")
        entry = _linked(_ok(engineer.get(_url(comp))))[oil["id"]]
        assert entry["last"]["value"] == "45"
        assert _by_type(_ok(engineer.get(_url(press))))[oil["id"]]["linked_by"] == [
            {"id": comp["id"], "code": comp["code"]}]

    def test_the_machine_is_the_source_of_a_component_under_a_unit(self, engineer, tree, hours):
        meters = _ok(_link(engineer, tree["part"], tree["press"], hours), 201)
        assert _linked(meters)[hours["id"]]["linked_from"]["id"] == tree["press"]["id"]

    def test_the_refusals_of_the_source(self, engineer, tree, oil, make_equipment, make_meter_type):
        press, unit_node, part, comp = tree["press"], tree["unit_node"], tree["part"], tree["comp"]
        assert _refusal(_link(engineer, press, press, oil)) == (
            400, None, "A machine has no node above it. Add the meter on the machine itself.")
        above = "Pick a node above this part."
        # a sibling, its own part (a child), another machine, itself, an unknown id
        for source in (comp, part, make_equipment(), unit_node, {"id": 99999999}):
            assert _refusal(_link(engineer, unit_node, source, oil)) == (400, "source_equipment_id", above)
        fuel = make_meter_type()
        assert _refusal(_link(engineer, comp, press, fuel)) == (
            409, "source_equipment_id", f"{press['code']} has no {fuel['name']} meter. Reload the page.")
        # a component unit's meter is not a source of a meter it has itself only through a link: no chains
        _ok(_link(engineer, unit_node, press, oil), 201)
        assert _refusal(_link(engineer, part, unit_node, oil)) == (
            409, "source_equipment_id", f"{unit_node['code']} has no {oil['name']} meter. Reload the page.")

    def test_one_meter_per_type_on_the_part(self, engineer, admin, tree, oil, hours, make_equipment):
        press, comp = tree["press"], tree["comp"]
        _ok(engineer.post(_url(comp), json={"meter_type_id": hours["id"]}), 201)
        assert _refusal(_link(engineer, comp, press, hours)) == (
            409, "meter_type_id", "This machine already has this meter")
        modelled = make_equipment(parent=press, level="component", model={"id": press["model_id"]})
        assert _refusal(_link(engineer, modelled, press, oil)) == (
            409, "meter_type_id", "This machine already has this meter")
        _ok(_link(engineer, comp, press, oil), 201)
        assert _refusal(_link(engineer, comp, press, oil)) == (
            409, "meter_type_id", f"This part already uses {press['code']}'s {oil['name']}. Remove that link first.")
        assert _refusal(engineer.post(_url(comp), json={"meter_type_id": oil["id"]})) == (
            409, "meter_type_id", f"This part uses {press['code']}'s {oil['name']}. Remove that link first.")
        assert _refusal(engineer.put(_url(comp, oil), json={"max_value": "50"})) == (
            409, None, f"This is {press['code']}'s meter. Set its limits on {press['code']}.")
        assert [e[0] for e in _events(admin, comp)] == ["meter_added", "meter_linked"]

    @pytest.mark.parametrize("field", ["meter_type_id", "source_equipment_id"])
    @pytest.mark.parametrize("bad", [None, True, "1", 0])
    def test_each_bad_body_field(self, engineer, tree, oil, field, bad):
        body = {"meter_type_id": oil["id"], "source_equipment_id": tree["press"]["id"], field: bad}
        assert _refusal(engineer.post(_links(tree["comp"]), json=body)) == (400, field, "Pick a meter")

    def test_an_unknown_meter_type(self, engineer, tree):
        body = {"meter_type_id": 99999999, "source_equipment_id": tree["press"]["id"]}
        assert _refusal(engineer.post(_links(tree["comp"]), json=body)) == (400, "meter_type_id", "Pick a meter")

    def test_who_may_link(self, tree, oil, at_unit, user_with_units, user_at_sites, make_unit, make_site, admin,
                          role_client, unit):
        press, comp = tree["press"], tree["comp"]
        assert _link(at_unit("maint_technician"), comp, press, oil).status_code == 403
        assert _link(user_with_units("maint_engineer", [make_unit()]), comp, press, oil).status_code == 404
        mixed, _ = user_at_sites([({"id": unit["site_id"]}, "maint_operator", [unit]),
                                  (make_site(), "maint_engineer", "all")])
        assert _link(mixed, comp, press, oil).status_code == 403
        assert _events(admin, comp) == []
        _ok(_link(role_client("it_admin"), comp, press, oil), 201)          # IT admin holds equipment:edit

    def test_a_scrapped_part_is_read_only(self, engineer, admin, tree, oil):
        _ok(admin.put(f"{EQUIPMENT}/{tree['comp']['id']}", json={"lifecycle": "scrapped"}))
        assert _refusal(_link(engineer, tree["comp"], tree["press"], oil)) == (409, None, SCRAPPED)

    def test_a_reading_of_a_linked_type_is_logged_on_the_source(self, engineer, tree, oil, at_unit):
        _ok(_link(engineer, tree["comp"], tree["press"], oil), 201)
        res = at_unit("maint_operator").post(f"{EQUIPMENT}/{tree['comp']['id']}/readings",
                                             json={"meter_type_id": oil["id"], "value": "45"})
        assert _refusal(res) == (409, "meter_type_id", "This machine does not have this meter. Reload the page.")

    def test_remove_the_link(self, engineer, admin, tree, oil):
        press, comp = tree["press"], tree["comp"]
        _ok(_link(engineer, comp, press, oil), 201)
        meters = _ok(engineer.delete(f"{_links(comp)}/{oil['id']}"))
        assert _linked(meters) == {}
        assert _events(admin, comp)[-1] == ("meter_unlinked", f"{oil['name']} from {press['code']}", None)
        assert engineer.delete(f"{_links(comp)}/{oil['id']}").status_code == 404

    def test_who_may_remove_a_link(self, tree, oil, at_unit, user_with_units, user_at_sites, make_unit, make_site,
                                   admin, unit, engineer):
        """A1.6.5: Remove link takes the key of Add link, at the part's site, through lock_node."""
        press, comp = tree["press"], tree["comp"]
        _ok(_link(engineer, comp, press, oil), 201)
        url = f"{_links(comp)}/{oil['id']}"
        mixed, _ = user_at_sites([({"id": unit["site_id"]}, "maint_operator", [unit]),
                                  (make_site(), "maint_engineer", "all")])
        for client, status in ((at_unit("maint_technician"), 403),
                               (user_with_units("maint_engineer", [make_unit()]), 404), (mixed, 403)):
            assert client.delete(url).status_code == status
            assert list(_linked(_ok(engineer.get(_url(comp))))) == [oil["id"]]
            assert [e[0] for e in _events(admin, comp)] == ["meter_linked"]
        _ok(admin.put(f"{EQUIPMENT}/{comp['id']}", json={"lifecycle": "scrapped"}))
        assert _refusal(engineer.delete(url)) == (409, None, SCRAPPED)

    def test_not_in_use_and_in_use_again(self, engineer, admin, tree, make_meter_type):
        # the source's own meter is removed, then added back; the part's model gains the type
        press, comp = tree["press"], tree["comp"]
        fuel = make_meter_type()
        _ok(engineer.post(_url(press), json={"meter_type_id": fuel["id"]}), 201)
        _ok(_link(engineer, comp, press, fuel), 201)
        _ok(engineer.put(_url(press, fuel), json={"active": False}))
        entry = _linked(_ok(engineer.get(_url(comp))))[fuel["id"]]
        assert (entry["in_use"], entry["not_in_use"], entry["limits_text"], entry["last"]) == (
            False, "no_source_meter", None, None)
        _ok(engineer.post(_url(press), json={"meter_type_id": fuel["id"]}), 201)
        assert _linked(_ok(engineer.get(_url(comp))))[fuel["id"]]["in_use"] is True
        _model_meter(admin, comp["model_id"], fuel)
        meters = _ok(engineer.get(_url(comp)))
        assert _linked(meters)[fuel["id"]]["not_in_use"] == "own"
        assert [m["source"] for m in meters if m["meter_type"]["id"] == fuel["id"]] == ["model", "linked"]
        assert _by_type(_ok(engineer.get(_url(press))))[fuel["id"]]["linked_by"] == []

    def test_used_by_names_the_plans_that_use_the_link(self, engineer, tree, oil, hours):
        """A1.6.5: LINK_PLANS_SQL (used_by) and needed_meters (the plans' meters) agree: the trigger and a Meter
        reading item count; an unlinked plan and an inactive template do not."""
        press, comp = tree["press"], tree["comp"]
        _ok(_link(engineer, comp, press, hours), 201)
        _ok(_link(engineer, comp, press, oil), 201)
        meter = {"trigger_kind": "meter", "calendar_every": None, "calendar_unit": None, "meter_type_id": hours["id"],
                 "meter_every": "250"}
        reading = {"item_type": "reading", "reading_kind": "meter", "text": "Oil", "meter_type_id": oil["id"]}
        names = {}
        for key, body in (("trigger", meter), ("item", {"items": [reading]}), ("removed", meter),
                          ("inactive", meter), ("calendar", {})):
            names[key] = make_template(engineer, **body)
        plans = {key: attach(engineer, comp, template) for key, template in names.items()}
        _ok(engineer.post(f"/api/pm/plans/{plans['removed']['id']}/remove"))
        _ok(engineer.put(f"/api/pm/templates/{names['inactive']['id']}", json={"active": False}))
        linked = _linked(_ok(engineer.get(_url(comp))))
        assert linked[hours["id"]]["used_by"] == [names["trigger"]["name"]]
        assert linked[oil["id"]]["used_by"] == [names["item"]["name"]]
        card = _ok(engineer.get("/api/pm/plans", query_string={"equipment_id": comp["id"]}))["items"]
        uses = {(m["meter_type"]["id"], p["template"]["name"]) for p in card if p["stop_remark"] is None
                for m in p["meters"] if m["equipment"] and m["equipment"]["id"] == press["id"]}
        assert uses == {(hours["id"], names["trigger"]["name"]), (oil["id"], names["item"]["name"])}

    def test_the_choices(self, engineer, tree, oil, hours, make_meter_type):
        press, part, unit_node = tree["press"], tree["part"], tree["unit_node"]
        assert _ok(engineer.get(f"{_links(press)}/choices")) == {"items": []}
        _ok(engineer.post(_url(part), json={"meter_type_id": hours["id"]}), 201)
        items = _ok(engineer.get(f"{_links(part)}/choices"))["items"]
        assert [(i["equipment"]["id"], i["meter_type"]["id"]) for i in items] == [(press["id"], oil["id"])]
        assert items[0]["equipment"]["level"] == "equipment" and items[0]["limits_text"] == "Limits: 10–60 °C"
        _ok(_link(engineer, part, press, oil), 201)
        assert _ok(engineer.get(f"{_links(part)}/choices"))["items"] == []
        # the nearest node first: the unit's own meter, then the press's
        fuel = make_meter_type()
        _ok(engineer.post(_url(unit_node), json={"meter_type_id": fuel["id"]}), 201)
        _ok(engineer.post(_url(press), json={"meter_type_id": fuel["id"]}), 201)
        items = _ok(engineer.get(f"{_links(part)}/choices"))["items"]
        assert [(i["equipment"]["id"], i["meter_type"]["id"]) for i in items] == [
            (unit_node["id"], fuel["id"]), (press["id"], fuel["id"])]

    def test_the_database_down_is_503(self, engineer, node, oil, db_down):
        assert engineer.get(f"{_links(node)}/choices").status_code == 503
        assert engineer.post(_links(node), json={"meter_type_id": oil["id"],
                                                 "source_equipment_id": 1}).status_code == 503
        assert engineer.delete(f"{_links(node)}/{oil['id']}").status_code == 503
