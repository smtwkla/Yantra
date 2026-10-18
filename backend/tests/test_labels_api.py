"""QR labels — the by-code lookup, the labels endpoint and the label link address setting
(S014), against the test DB."""

import logging

import pytest

import config
from labels_core import MAX_LABELS_PER_REQUEST
from local_db import get_local_db
from settings import DEFAULT_LABEL_BASE_URL

EQUIPMENT = "/api/equipment"
BY_CODE = f"{EQUIPMENT}/by-code"
LABELS = f"{EQUIPMENT}/labels"
SETTING = "/api/settings/labels"
NOT_FOUND = "Some of the selected equipment was not found or is not at your units"


def _write_address(value):
    """Store ``value`` as the label_base_url row as is (None removes the row)."""
    conn = get_local_db(config.DB_CONFIG)
    try:
        with conn.cursor() as cur:
            if value is None:
                cur.execute("DELETE FROM app_settings WHERE setting_key = 'label_base_url'")
            else:
                cur.execute("INSERT INTO app_settings (setting_key, setting_value) VALUES ('label_base_url', %s) "
                            "ON DUPLICATE KEY UPDATE setting_value = %s", (value, value))
    finally:
        conn.close()


@pytest.fixture
def label_address():
    """label_address(text) stores the address row as is; the row is deleted afterwards, so
    every test starts from the default (no row)."""
    _write_address(None)
    yield _write_address
    _write_address(None)


def _labels(client, ids, with_parts=None):
    body = {"ids": [n["id"] for n in ids]}
    if with_parts is not None:
        body["with_parts"] = with_parts
    return client.post(LABELS, json=body)


def _label_ids(res):
    assert res.status_code == 200, res.get_json()
    return [label["id"] for label in res.get_json()["labels"]]


@pytest.fixture
def tree(make_equipment, admin, unit):
    """A press in ``unit`` with a gearbox (holding a live seal and a scrapped bearing) and a motor."""
    press = make_equipment(unit=unit)
    gearbox = make_equipment(parent=press, name="Gearbox")
    motor = make_equipment(parent=press, name="Motor")
    seal = make_equipment(parent=gearbox, level="component", name="Seal")
    bearing = make_equipment(parent=gearbox, level="component", name="Bearing")
    assert admin.put(f"{EQUIPMENT}/{bearing['id']}", json={"status": "scrapped"}).status_code == 200
    return {"press": press, "gearbox": gearbox, "motor": motor, "seal": seal, "bearing": bearing}


class TestByCode:

    def test_found(self, admin, node):
        res = admin.get(f"{BY_CODE}/{node['code']}")
        assert res.status_code == 200
        assert res.get_json() == {"id": node["id"]}

    def test_lower_case_is_accepted(self, admin, node):
        assert admin.get(f"{BY_CODE}/{node['code'].lower()}").get_json() == {"id": node["id"]}

    def test_unknown_is_404(self, admin):
        assert admin.get(f"{BY_CODE}/ZZZZ99999999").status_code == 404

    @pytest.mark.parametrize("code", ["V1", "VBM-001", "ABCDE001", "ABCD123456789", "001VBM"])
    def test_malformed_is_404(self, admin, code):
        assert admin.get(f"{BY_CODE}/{code}").status_code == 404

    def test_a_unit_the_user_lacks_is_the_same_404(self, admin, user_with_units, make_unit, node):
        engineer = user_with_units("maint_engineer", [make_unit()])
        refused = engineer.get(f"{BY_CODE}/{node['code']}")
        unknown = engineer.get(f"{BY_CODE}/ZZZZ99999999")
        assert refused.status_code == unknown.status_code == 404
        assert refused.get_json() == unknown.get_json()

    def test_no_units_at_all_is_the_same_404(self, admin, user_with_units, node):
        nobody = user_with_units("maint_engineer", [])
        refused = nobody.get(f"{BY_CODE}/{node['code']}")
        unknown = nobody.get(f"{BY_CODE}/ZZZZ99999999")
        assert refused.status_code == unknown.status_code == 404
        assert refused.get_json() == unknown.get_json()

    def test_at_their_unit(self, at_unit, node):
        assert at_unit("maint_operator").get(f"{BY_CODE}/{node['code']}").get_json() == {"id": node["id"]}

    def test_a_scrapped_node_still_resolves(self, admin, make_equipment):
        node = make_equipment()
        assert admin.put(f"{EQUIPMENT}/{node['id']}", json={"status": "scrapped"}).status_code == 200
        assert admin.get(f"{BY_CODE}/{node['code']}").get_json() == {"id": node["id"]}


class TestLabels:

    def test_one_label_and_its_fields(self, admin, node, label_address):
        res = _labels(admin, [node])
        assert res.status_code == 200, res.get_json()
        [label] = res.get_json()["labels"]
        assert label["id"] == node["id"]
        assert label["code"] == node["code"]
        assert label["name"] == node["name"]
        assert label["site_code"] == node["unit"].split(".")[0]
        assert label["url"] == f"{DEFAULT_LABEL_BASE_URL}/e/{node['code']}"
        assert label["qr_svg"].startswith("<svg") and "viewBox" in label["qr_svg"]

    def test_the_stored_address_is_used(self, admin, node, label_address):
        label_address("http://10.24.1.5:5176")
        [label] = _labels(admin, [node]).get_json()["labels"]
        assert label["url"] == f"http://10.24.1.5:5176/e/{node['code']}"

    def test_without_parts(self, admin, tree):
        assert _label_ids(_labels(admin, [tree["press"]])) == [tree["press"]["id"]]
        assert _label_ids(_labels(admin, [tree["press"]], with_parts=False)) == [tree["press"]["id"]]

    def test_with_parts_in_order_scrapped_part_left_out(self, admin, tree):
        ids = _label_ids(_labels(admin, [tree["press"]], with_parts=True))
        children = sorted([tree["gearbox"], tree["motor"]], key=lambda n: n["code"])
        assert ids == [tree["press"]["id"], *[c["id"] for c in children], tree["seal"]["id"]]
        assert tree["bearing"]["id"] not in ids

    def test_a_parent_and_its_part_both_selected_give_one_each(self, admin, tree):
        ids = _label_ids(_labels(admin, [tree["press"], tree["gearbox"]], with_parts=True))
        assert len(ids) == len(set(ids)) == 4

    def test_a_selected_scrapped_node_is_printed(self, admin, tree):
        assert _label_ids(_labels(admin, [tree["bearing"]], with_parts=True)) == [tree["bearing"]["id"]]

    def test_selection_order_is_kept(self, admin, make_equipment):
        first, second = make_equipment(), make_equipment()
        assert _label_ids(_labels(admin, [second, first])) == [second["id"], first["id"]]

    @pytest.mark.parametrize("body", [
        {}, {"ids": []}, {"ids": [1, 1]}, {"ids": ["1"]}, {"ids": [1.5]}, {"ids": [True]}, {"ids": [0]},
        {"ids": [-3]}, {"ids": 5}, {"ids": [1], "with_parts": "yes"}, {"ids": [1], "with_parts": 1},
    ])
    def test_a_bad_body_is_400(self, admin, body):
        assert admin.post(LABELS, json=body).status_code == 400

    def test_over_the_cap_before_expansion_is_400(self, admin):
        res = admin.post(LABELS, json={"ids": list(range(1, MAX_LABELS_PER_REQUEST + 2))})
        assert res.status_code == 400
        assert "Too many labels" in res.get_json()["error"]

    def test_over_the_cap_after_expansion_is_400(self, admin, make_equipment, make_model, monkeypatch):
        # A lower cap for this test, so it needs a few parts rather than 300
        import labels_core
        monkeypatch.setattr(labels_core, "MAX_LABELS_PER_REQUEST", 2)
        press = make_equipment()
        make_equipment(parent=press)
        make_equipment(parent=press)
        res = _labels(admin, [press], with_parts=True)
        assert res.status_code == 400
        assert "Too many labels" in res.get_json()["error"]
        assert _labels(admin, [press]).status_code == 200

    def test_an_unknown_id_is_404_for_all(self, admin, node):
        res = admin.post(LABELS, json={"ids": [node["id"], 999999999]})
        assert res.status_code == 404
        assert res.get_json()["error"] == NOT_FOUND

    def test_a_node_outside_the_users_units_is_404_naming_none(self, user_with_units, make_unit, make_equipment):
        unit_a, unit_b = make_unit(), make_unit()
        mine, theirs = make_equipment(unit=unit_a), make_equipment(unit=unit_b)
        engineer = user_with_units("maint_engineer", [unit_a])
        assert _label_ids(_labels(engineer, [mine])) == [mine["id"]]
        res = _labels(engineer, [mine, theirs])
        assert res.status_code == 404
        assert res.get_json() == {"error": NOT_FOUND}

    def test_parts_follow_the_roots_unit(self, at_unit, tree):
        engineer = at_unit("maint_engineer")
        assert len(_label_ids(_labels(engineer, [tree["press"]], with_parts=True))) == 4
        assert _label_ids(_labels(engineer, [tree["seal"]])) == [tree["seal"]["id"]]

    def test_a_user_with_no_units_gets_404_not_an_sql_error(self, user_with_units, node):
        engineer = user_with_units("maint_engineer", [])
        res = _labels(engineer, [node])
        assert res.status_code == 404
        assert res.get_json() == {"error": NOT_FOUND}

    @pytest.mark.parametrize("role", ["admin", "it_admin", "maint_manager"])
    def test_every_unit_roles_pass(self, user_with_units, node, role):
        assert _label_ids(_labels(user_with_units(role, []), [node])) == [node["id"]]


class TestLabelSetting:

    @pytest.mark.parametrize("role", ["maint_manager", "it_admin"])
    def test_the_default_before_any_save(self, role_client, label_address, role):
        res = role_client(role).get(SETTING)
        assert res.status_code == 200
        assert res.get_json() == {"base_url": DEFAULT_LABEL_BASE_URL}

    def test_operator_may_not_read(self, role_client):
        assert role_client("maint_operator").get(SETTING).status_code == 403

    def test_save_normalises_and_logs(self, admin, label_address, caplog):
        caplog.set_level(logging.INFO, logger="settings")
        res = admin.put(SETTING, json={"base_url": " HTTPS://Yantra.Example.in/ "})
        assert res.status_code == 200, res.get_json()
        assert res.get_json() == {"base_url": "https://yantra.example.in"}
        assert admin.get(SETTING).get_json() == {"base_url": "https://yantra.example.in"}
        assert any(r.levelname == "INFO" and
                   "label_base_url changed by test_it_admin: None -> https://yantra.example.in" in r.getMessage()
                   for r in caplog.records)

    @pytest.mark.parametrize("value", ["https://x.in/path", "ftp://x.in", "https://u@x.in", "x.in", "", None, 5,
                                       "https://" + "a" * 40 + ".in"])
    def test_a_bad_address_is_400(self, admin, label_address, value):
        res = admin.put(SETTING, json={"base_url": value})
        assert res.status_code == 400
        assert res.get_json()["field"] == "base_url"

    def test_manager_may_not_save(self, role_client, label_address):
        assert role_client("maint_manager").put(SETTING, json={"base_url": "https://x.in"}).status_code == 403

    def test_a_corrupt_stored_value_gives_the_default_with_a_warning(self, admin, label_address, caplog):
        label_address("https://x.in/not allowed")
        assert admin.get(SETTING).get_json() == {"base_url": DEFAULT_LABEL_BASE_URL}
        assert any(r.levelname == "WARNING" and "label_base_url" in r.getMessage() for r in caplog.records)
