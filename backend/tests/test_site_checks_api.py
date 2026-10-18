"""Rights follow the record's site (S011 § 5.2–§ 5.4), against the test DB.

The user is an engineer at site A and an operator at site B, with real memberships
(user_at_sites, as maintenance_team): they read at both and write only at A.  One case per
choke point (load_node_for_user, _load_target_node, _lock_target_unit) and the routes on top.

Needs the dev MariaDB container (tooling/dev/dev-db-up.bat).
"""

import pytest

import config_rbac
from auth_utils import compute_permissions
from tests.documents_helpers import EQUIPMENT, docs_url, folder_files, upload, uploaded

REMOVED = f"{EQUIPMENT}/removed-documents"


@pytest.fixture
def world(make_site, make_unit, make_equipment, make_class, make_model):
    site_a, site_b = make_site(), make_site()
    unit_a, unit_b = make_unit(site_a), make_unit(site_b)
    cls = make_class()
    model = make_model(cls=cls)
    return {
        "site_a": site_a, "site_b": site_b, "unit_a": unit_a, "unit_b": unit_b, "cls": cls, "model": model,
        "other_model": make_model(),   # of another class
        "mill_a": make_equipment(unit=unit_a, model=model), "mill_b": make_equipment(unit=unit_b, model=model),
    }


@pytest.fixture
def user(user_at_sites, world):
    client, _ = user_at_sites([(world["site_a"], "maint_engineer", [world["unit_a"]]),
                               (world["site_b"], "maint_operator", [world["unit_b"]])])
    return client


def _refused_at(res, site, field=None):
    assert res.status_code == 403, res.get_json()
    assert res.get_json()["error"] == f"You can't do this at {site['code']}"
    assert res.get_json().get("field") == field


class TestEquipmentWrites:

    def test_edit_at_a_but_not_at_b(self, user, world):
        assert user.put(f"{EQUIPMENT}/{world['mill_a']['id']}", json={"name": "Edited"}).status_code == 200
        _refused_at(user.put(f"{EQUIPMENT}/{world['mill_b']['id']}", json={"name": "x"}), world["site_b"])

    def test_read_at_b(self, user, world):
        assert user.get(f"{EQUIPMENT}/{world['mill_b']['id']}").status_code == 200

    @pytest.mark.parametrize("body", [{"status": "standby"}, {"notes": "Bearing 6205"}, {"model_id": "other"},
                                      {"criticality": "A"}])
    def test_status_notes_model_at_b(self, user, world, body):
        if body.get("model_id") == "other":
            # A model of another class: a reclassification, refused at B (BR3-03)
            body = {"model_id": world["other_model"]["id"]}
        _refused_at(user.put(f"{EQUIPMENT}/{world['mill_b']['id']}", json=body), world["site_b"])

    def test_create_in_a_unit_at_b(self, user, world):
        res = user.post(EQUIPMENT, json={"level": "equipment", "unit_id": world["unit_b"]["id"],
                                         "model_id": world["model"]["id"], "name": "x"})
        _refused_at(res, world["site_b"], "unit_id")
        res = user.post(EQUIPMENT, json={"level": "equipment", "unit_id": world["unit_a"]["id"],
                                         "model_id": world["model"]["id"], "name": "x"})
        assert res.status_code == 201

    def test_part_under_a_parent_at_b(self, user, world):
        res = user.post(EQUIPMENT, json={"level": "component", "parent_id": world["mill_b"]["id"],
                                         "model_id": world["model"]["id"], "name": "x"})
        _refused_at(res, world["site_b"], "parent_id")

    def test_move_between_sites(self, user, world):
        # From A to B: the target unit's site
        _refused_at(user.put(f"{EQUIPMENT}/{world['mill_a']['id']}", json={"unit_id": world["unit_b"]["id"]}),
                    world["site_b"], "unit_id")
        # From B to A: the node's own site
        _refused_at(user.put(f"{EQUIPMENT}/{world['mill_b']['id']}", json={"unit_id": world["unit_a"]["id"]}),
                    world["site_b"])

    def test_reparent_to_a_parent_at_b(self, user, world, make_equipment):
        part = make_equipment(parent=world["mill_a"], level="component")
        _refused_at(user.put(f"{EQUIPMENT}/{part['id']}", json={"parent_id": world["mill_b"]["id"]}),
                    world["site_b"], "parent_id")

    def test_node_permissions_follow_the_site(self, user, world):
        at_a = user.get(f"{EQUIPMENT}/{world['mill_a']['id']}").get_json()["permissions"]
        at_b = user.get(f"{EQUIPMENT}/{world['mill_b']['id']}").get_json()["permissions"]
        assert "equipment:edit" in at_a and "equipment:edit" not in at_b
        assert "equipment:read" in at_b

    def test_token_roles_hold_at_every_site(self, admin, role_client, world):
        perms = admin.get(f"{EQUIPMENT}/{world['mill_b']['id']}").get_json()["permissions"]
        assert perms == compute_permissions(["it_admin"])
        perms = role_client("admin").get(f"{EQUIPMENT}/{world['mill_b']['id']}").get_json()["permissions"]
        assert set(perms) == set(config_rbac.PERMISSIONS)


class TestDocumentWrites:

    def test_upload_at_b_is_refused_and_writes_no_file(self, user, world):
        _refused_at(upload(user, world["mill_b"]), world["site_b"])
        assert folder_files(world["mill_b"]) == []
        assert upload(user, world["mill_a"]).status_code == 201

    def test_title_and_remove_at_b(self, admin, user, world):
        doc = uploaded(admin, world["mill_b"])
        url = f"{docs_url(world['mill_b'])}/{doc['id']}"
        _refused_at(user.put(url, json={"title": "x"}), world["site_b"])
        _refused_at(user.delete(url), world["site_b"])
        assert user.get(f"{url}/file").status_code == 200   # reading at B is allowed


class TestRemovedDocumentsBySite:
    """BR1-03: a manager at A, operator at B sees and acts on A's removed documents only."""

    @pytest.fixture
    def manager(self, user_at_sites, world):
        client, _ = user_at_sites([(world["site_a"], "maint_manager", "all"),
                                   (world["site_b"], "maint_operator", "all")])
        return client

    def _removed(self, admin, node):
        doc = uploaded(admin, node, title=f"Removed {node['code']}")
        assert admin.delete(f"{docs_url(node)}/{doc['id']}").status_code == 204
        return doc

    def test_list_restore_and_purge(self, admin, manager, world):
        at_a, at_b = self._removed(admin, world["mill_a"]), self._removed(admin, world["mill_b"])
        listed = {i["id"] for i in manager.get(REMOVED, query_string={"q": world["cls"]["code"]}).get_json()["items"]}
        assert at_a["id"] in listed and at_b["id"] not in listed
        base_b = f"{docs_url(world['mill_b'])}/{at_b['id']}"
        _refused_at(manager.post(f"{base_b}/restore"), world["site_b"])
        _refused_at(manager.post(f"{base_b}/purge"), world["site_b"])
        assert manager.post(f"{docs_url(world['mill_a'])}/{at_a['id']}/purge").status_code == 204

    def test_restore_at_a(self, admin, manager, world):
        doc = self._removed(admin, world["mill_a"])
        assert manager.post(f"{docs_url(world['mill_a'])}/{doc['id']}/restore").status_code == 200
