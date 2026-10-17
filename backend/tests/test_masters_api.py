"""Masters API — sites, units, equipment classes, unit access, against the test DB.

Needs the dev MariaDB container (tooling/dev/dev-db-up.bat).  Codes and
warehouse names come from the ``uniq`` fixture, never fixed values.
"""


import pymysql
import pytest

import config
from local_db import get_local_db
from tests.access_helpers import site_rows

BASE = "/api/masters"


def _row(sql, params):
    """Read straight from the DB, bypassing the API."""
    conn = get_local_db(config.DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone()
    finally:
        conn.close()


class TestSites:

    def test_create_list_edit(self, admin, uniq):
        code = uniq.site_code()
        created = admin.post(f"{BASE}/sites", json={"code": code.lower(), "name": " Main ", "address": "Karur"})
        assert created.status_code == 201
        site = created.get_json()
        assert (site["code"], site["name"], site["address"], site["active"]) == (code, "Main", "Karur", 1)

        listed = admin.get(f"{BASE}/sites").get_json()
        assert listed["total"] == len(listed["items"])
        assert code in [s["code"] for s in listed["items"]]

        edited = admin.put(f"{BASE}/sites/{site['id']}", json={"name": "Main factory"})
        assert edited.status_code == 200
        assert edited.get_json()["name"] == "Main factory"
        assert edited.get_json()["code"] == code

    def test_list_is_ordered_by_code(self, admin, make_site):
        make_site()
        make_site()
        codes = [s["code"] for s in admin.get(f"{BASE}/sites").get_json()["items"]]
        assert codes == sorted(codes)

    def test_duplicate_code_is_409_with_field(self, admin, make_site):
        site = make_site()
        res = admin.post(f"{BASE}/sites", json={"code": site["code"], "name": "Other"})
        assert res.status_code == 409
        assert res.get_json()["field"] == "code"
        assert "site" in res.get_json()["error"]

    def test_invalid_code_is_400_with_field(self, admin):
        res = admin.post(f"{BASE}/sites", json={"code": "A.B", "name": "x"})
        assert res.status_code == 400
        assert res.get_json()["field"] == "code"

    def test_body_must_be_an_object(self, admin):
        assert admin.post(f"{BASE}/sites", json=[1]).status_code == 400

    def test_unknown_site_is_404(self, admin):
        assert admin.put(f"{BASE}/sites/999999", json={"name": "x"}).status_code == 404

    def test_inactive_hidden_unless_requested(self, admin, make_site):
        site = make_site()
        admin.put(f"{BASE}/sites/{site['id']}", json={"active": False})
        ids = [s["id"] for s in admin.get(f"{BASE}/sites").get_json()["items"]]
        assert site["id"] not in ids
        ids = [s["id"] for s in admin.get(f"{BASE}/sites?include_inactive=1").get_json()["items"]]
        assert site["id"] in ids

    def test_reactivate(self, admin, make_site):
        site = make_site()
        admin.put(f"{BASE}/sites/{site['id']}", json={"active": False})
        res = admin.put(f"{BASE}/sites/{site['id']}", json={"active": True})
        assert res.get_json()["active"] == 1


class TestAuditColumns:

    def test_created_set_updated_null_until_first_edit(self, admin, make_site):
        site = make_site()
        assert site["created_by"] == "test_it_admin"
        assert site["created_at"]
        assert site["updated_at"] is None and site["updated_by"] is None

        edited = admin.put(f"{BASE}/sites/{site['id']}", json={"name": "Renamed"}).get_json()
        assert edited["updated_by"] == "test_it_admin"
        assert edited["updated_at"]
        assert edited["created_by"] == "test_it_admin"

    def test_actor_comes_from_the_token_not_the_body(self, admin, uniq):
        res = admin.post(f"{BASE}/sites", json={"code": uniq.site_code(), "name": "x", "created_by": "mallory"})
        assert res.get_json()["created_by"] == "test_it_admin"

    def test_class_edit_by_engineer_records_engineer(self, engineer, uniq):
        created = engineer.post(f"{BASE}/equipment-classes", json={"code": uniq.class_code(), "name": "x"}).get_json()
        edited = engineer.put(f"{BASE}/equipment-classes/{created['id']}", json={"name": "y"}).get_json()
        assert edited["updated_by"] == "test_maint_engineer"


class TestSiteCodeFreeze:

    def test_site_without_units_can_change_code(self, admin, make_site, uniq):
        site = make_site()
        new_code = uniq.site_code()
        res = admin.put(f"{BASE}/sites/{site['id']}", json={"code": new_code})
        assert res.status_code == 200
        assert res.get_json()["code"] == new_code

    def test_site_with_a_unit_cannot_change_code(self, admin, make_site, make_unit, uniq):
        site = make_site()
        make_unit(site)
        res = admin.put(f"{BASE}/sites/{site['id']}", json={"code": uniq.site_code()})
        assert res.status_code == 409
        assert res.get_json()["field"] == "code"

    def test_inactive_unit_still_counts_as_a_reference(self, admin, make_site, make_unit, uniq):
        site = make_site()
        unit = make_unit(site)
        admin.put(f"{BASE}/units/{unit['id']}", json={"active": False})
        assert admin.put(f"{BASE}/sites/{site['id']}", json={"code": uniq.site_code()}).status_code == 409

    def test_unchanged_code_or_no_code_is_accepted(self, admin, make_site, make_unit):
        site = make_site()
        make_unit(site)
        assert admin.put(f"{BASE}/sites/{site['id']}", json={"code": site["code"], "name": "A"}).status_code == 200
        assert admin.put(f"{BASE}/sites/{site['id']}", json={"name": "B"}).status_code == 200
        assert admin.put(f"{BASE}/sites/{site['id']}", json={"code": site["code"].lower()}).status_code == 200


class TestUnits:

    def test_create_list_edit_with_derived_full_code(self, admin, make_site, uniq):
        site = make_site()
        code = uniq.unit_code()
        created = admin.post(f"{BASE}/units", json={"site_id": site["id"], "code": code, "name": "Flour mill"})
        assert created.status_code == 201
        unit = created.get_json()
        assert unit["full_code"] == f"{site['code']}.{code}"
        assert unit["site_code"] == site["code"]
        assert unit["oneerp_warehouse"] is None

        edited = admin.put(f"{BASE}/units/{unit['id']}", json={"name": "Flour mill 1"})
        assert edited.status_code == 200
        assert edited.get_json()["name"] == "Flour mill 1"
        assert edited.get_json()["full_code"] == unit["full_code"]

    def test_list_filters_by_site(self, admin, make_site, make_unit):
        site_a, site_b = make_site(), make_site()
        unit_a = make_unit(site_a)
        make_unit(site_b)
        items = admin.get(f"{BASE}/units?site_id={site_a['id']}").get_json()["items"]
        assert [u["id"] for u in items] == [unit_a["id"]]

    def test_list_without_filter_returns_all_sites_units(self, admin, make_site, make_unit):
        unit_a, unit_b = make_unit(), make_unit()
        ids = [u["id"] for u in admin.get(f"{BASE}/units").get_json()["items"]]
        assert {unit_a["id"], unit_b["id"]} <= set(ids)

    def test_bad_site_filter_is_400(self, admin):
        assert admin.get(f"{BASE}/units?site_id=abc").status_code == 400

    def test_duplicate_code_in_same_site_is_409_but_other_site_is_fine(self, admin, make_site, make_unit):
        site, other = make_site(), make_site()
        unit = make_unit(site)
        dup = admin.post(f"{BASE}/units", json={"site_id": site["id"], "code": unit["code"], "name": "x"})
        assert dup.status_code == 409
        assert dup.get_json()["field"] == "code"
        assert "site" in dup.get_json()["error"]
        ok = admin.post(f"{BASE}/units", json={"site_id": other["id"], "code": unit["code"], "name": "x"})
        assert ok.status_code == 201

    def test_duplicate_warehouse_is_409_with_its_own_field(self, admin, make_unit, uniq):
        warehouse = uniq.warehouse()
        make_unit(oneerp_warehouse=warehouse)
        site = admin.get(f"{BASE}/sites").get_json()["items"][0]
        res = admin.post(f"{BASE}/units", json={"site_id": site["id"], "code": uniq.unit_code(),
                                                "name": "x", "oneerp_warehouse": warehouse})
        assert res.status_code == 409
        assert res.get_json()["field"] == "oneerp_warehouse"

    def test_many_units_may_have_no_warehouse(self, make_unit):
        make_unit()
        make_unit()

    def test_warehouse_is_not_upper_cased(self, make_unit, uniq):
        warehouse = uniq.warehouse()
        assert make_unit(oneerp_warehouse=f"  {warehouse}  ")["oneerp_warehouse"] == warehouse

    def test_unknown_site_is_400(self, admin, uniq):
        res = admin.post(f"{BASE}/units", json={"site_id": 999999, "code": uniq.unit_code(), "name": "x"})
        assert res.status_code == 400
        assert res.get_json()["field"] == "site_id"

    def test_invalid_code_is_400(self, admin, make_site):
        res = admin.post(f"{BASE}/units", json={"site_id": make_site()["id"], "code": "M", "name": "x"})
        assert res.status_code == 400
        assert res.get_json()["field"] == "code"

    def test_unknown_unit_is_404(self, admin):
        assert admin.put(f"{BASE}/units/999999", json={"name": "x"}).status_code == 404


class TestUnitCodeFreeze:

    def test_unit_without_access_rows_can_change_code(self, admin, make_unit, uniq):
        unit = make_unit()
        new_code = uniq.unit_code()
        res = admin.put(f"{BASE}/units/{unit['id']}", json={"code": new_code})
        assert res.status_code == 200
        assert res.get_json()["code"] == new_code

    def test_unit_without_access_rows_can_move_to_another_active_site(self, admin, make_unit, make_site):
        unit, target = make_unit(), make_site()
        res = admin.put(f"{BASE}/units/{unit['id']}", json={"site_id": target["id"]})
        assert res.status_code == 200
        assert res.get_json()["site_code"] == target["code"]

    def test_move_to_an_inactive_site_is_409(self, admin, make_unit, make_site):
        unit, target = make_unit(), make_site()
        admin.put(f"{BASE}/sites/{target['id']}", json={"active": False})
        res = admin.put(f"{BASE}/units/{unit['id']}", json={"site_id": target["id"]})
        assert res.status_code == 409

    def test_move_that_collides_with_a_unit_in_the_target_site_is_409(self, admin, make_unit, make_site):
        target = make_site()
        unit = make_unit()
        clash = make_unit(target, code=unit["code"])
        res = admin.put(f"{BASE}/units/{unit['id']}", json={"site_id": clash["site_id"]})
        assert res.status_code == 409
        assert res.get_json()["field"] == "code"

    def test_unit_with_access_rows_cannot_change_code_or_site(self, admin, make_unit, make_site, make_person, uniq):
        unit = make_unit()
        make_person(username=uniq.username(), sites=site_rows("maint_operator", [unit]))
        by_code = admin.put(f"{BASE}/units/{unit['id']}", json={"code": uniq.unit_code()})
        assert by_code.status_code == 409 and by_code.get_json()["field"] == "code"
        by_site = admin.put(f"{BASE}/units/{unit['id']}", json={"site_id": make_site()["id"]})
        assert by_site.status_code == 409 and by_site.get_json()["field"] == "site_id"

    def test_unchanged_code_or_site_is_accepted_when_in_use(self, admin, make_unit, make_person, uniq):
        unit = make_unit()
        make_person(username=uniq.username(), sites=site_rows("maint_operator", [unit]))
        res = admin.put(f"{BASE}/units/{unit['id']}",
                        json={"code": unit["code"], "site_id": unit["site_id"], "name": "Renamed"})
        assert res.status_code == 200
        assert admin.put(f"{BASE}/units/{unit['id']}", json={"name": "Again"}).status_code == 200


    def test_unit_with_equipment_cannot_change_code_or_site(self, admin, make_unit, make_site,
                                                            make_equipment, uniq):
        unit = make_unit()
        make_equipment(unit=unit)
        by_code = admin.put(f"{BASE}/units/{unit['id']}", json={"code": uniq.unit_code()})
        assert by_code.status_code == 409 and by_code.get_json()["field"] == "code"
        by_site = admin.put(f"{BASE}/units/{unit['id']}", json={"site_id": make_site()["id"]})
        assert by_site.status_code == 409 and by_site.get_json()["field"] == "site_id"

    def test_scrapped_equipment_still_freezes_the_unit(self, admin, make_unit, make_equipment, uniq):
        unit = make_unit()
        node = make_equipment(unit=unit)
        assert admin.put(f"/api/equipment/{node['id']}", json={"status": "scrapped"}).status_code == 200
        assert admin.put(f"{BASE}/units/{unit['id']}", json={"code": uniq.unit_code()}).status_code == 409


class TestActivationRules:

    def test_site_with_active_units_cannot_be_deactivated(self, admin, make_site, make_unit):
        site = make_site()
        unit = make_unit(site)
        res = admin.put(f"{BASE}/sites/{site['id']}", json={"active": False})
        assert res.status_code == 409
        admin.put(f"{BASE}/units/{unit['id']}", json={"active": False})
        assert admin.put(f"{BASE}/sites/{site['id']}", json={"active": False}).status_code == 200

    def test_unit_cannot_be_created_under_an_inactive_site(self, admin, make_site, uniq):
        site = make_site()
        admin.put(f"{BASE}/sites/{site['id']}", json={"active": False})
        res = admin.post(f"{BASE}/units", json={"site_id": site["id"], "code": uniq.unit_code(), "name": "x"})
        assert res.status_code == 409

    def test_unit_cannot_be_reactivated_under_an_inactive_site(self, admin, make_site, make_unit):
        site = make_site()
        unit = make_unit(site)
        admin.put(f"{BASE}/units/{unit['id']}", json={"active": False})
        admin.put(f"{BASE}/sites/{site['id']}", json={"active": False})
        assert admin.put(f"{BASE}/units/{unit['id']}", json={"active": True}).status_code == 409
        admin.put(f"{BASE}/sites/{site['id']}", json={"active": True})
        assert admin.put(f"{BASE}/units/{unit['id']}", json={"active": True}).status_code == 200

    def test_inactive_units_hidden_unless_requested(self, admin, make_unit):
        unit = make_unit()
        admin.put(f"{BASE}/units/{unit['id']}", json={"active": False})
        assert unit["id"] not in [u["id"] for u in admin.get(f"{BASE}/units").get_json()["items"]]
        assert unit["id"] in [u["id"] for u in admin.get(f"{BASE}/units?include_inactive=1").get_json()["items"]]


    @pytest.mark.parametrize("status", ["in_service", "standby", "out_of_use"])
    def test_unit_holding_equipment_not_scrapped_cannot_be_deactivated(self, admin, make_unit, make_equipment,
                                                                       status):
        unit = make_unit()
        make_equipment(unit=unit, status=status)
        res = admin.put(f"{BASE}/units/{unit['id']}", json={"active": False})
        assert res.status_code == 409
        assert res.get_json()["field"] == "active"

    def test_unit_with_only_scrapped_equipment_can_be_deactivated(self, admin, make_unit, make_equipment):
        unit = make_unit()
        node = make_equipment(unit=unit)
        admin.put(f"/api/equipment/{node['id']}", json={"status": "scrapped"})
        assert admin.put(f"{BASE}/units/{unit['id']}", json={"active": False}).status_code == 200


class TestEquipmentClasses:

    def test_create_list_edit(self, engineer, uniq):
        code = uniq.class_code()
        created = engineer.post(f"{BASE}/equipment-classes", json={"code": code.lower(), "name": "Vibrating mill"})
        assert created.status_code == 201
        record = created.get_json()
        assert record["code"] == code
        assert code in [c["code"] for c in engineer.get(f"{BASE}/equipment-classes").get_json()["items"]]

        edited = engineer.put(f"{BASE}/equipment-classes/{record['id']}", json={"name": "Mill", "code": "ZZ"})
        assert edited.status_code == 200
        assert (edited.get_json()["name"], edited.get_json()["code"]) == ("Mill", "ZZ")

    def test_duplicate_code_is_409(self, engineer, uniq):
        code = uniq.class_code()
        engineer.post(f"{BASE}/equipment-classes", json={"code": code, "name": "x"})
        res = engineer.post(f"{BASE}/equipment-classes", json={"code": code, "name": "y"})
        assert res.status_code == 409
        assert res.get_json()["field"] == "code"

    def test_five_letter_code_is_400(self, engineer):
        res = engineer.post(f"{BASE}/equipment-classes", json={"code": "ABCDE", "name": "x"})
        assert res.status_code == 400
        assert res.get_json()["field"] == "code"

    def test_deactivate_and_include_inactive(self, engineer, uniq):
        record = engineer.post(f"{BASE}/equipment-classes", json={"code": uniq.class_code(), "name": "x"}).get_json()
        engineer.put(f"{BASE}/equipment-classes/{record['id']}", json={"active": False})
        assert record["id"] not in [c["id"] for c in engineer.get(f"{BASE}/equipment-classes").get_json()["items"]]
        listed = engineer.get(f"{BASE}/equipment-classes?include_inactive=1").get_json()["items"]
        assert record["id"] in [c["id"] for c in listed]

    def test_unknown_class_is_404(self, engineer):
        assert engineer.put(f"{BASE}/equipment-classes/999999", json={"name": "x"}).status_code == 404


    def test_class_with_equipment_cannot_change_code(self, engineer, make_class, make_equipment, uniq):
        cls = make_class()
        make_equipment(cls=cls)
        res = engineer.put(f"{BASE}/equipment-classes/{cls['id']}", json={"code": uniq.class_code()})
        assert res.status_code == 409
        assert res.get_json()["field"] == "code"
        # Unchanged code and other fields are fine
        assert engineer.put(f"{BASE}/equipment-classes/{cls['id']}",
                            json={"code": cls["code"], "name": "Renamed"}).status_code == 200

    def test_scrapped_equipment_still_freezes_the_class(self, admin, engineer, make_class, make_equipment, uniq):
        cls = make_class()
        node = make_equipment(cls=cls)
        admin.put(f"/api/equipment/{node['id']}", json={"status": "scrapped"})
        res = engineer.put(f"{BASE}/equipment-classes/{cls['id']}", json={"code": uniq.class_code()})
        assert res.status_code == 409

    def test_deactivated_class_with_equipment_stays_frozen(self, engineer, make_class, make_equipment, uniq):
        cls = make_class()
        make_equipment(cls=cls)
        engineer.put(f"{BASE}/equipment-classes/{cls['id']}", json={"active": False})
        res = engineer.put(f"{BASE}/equipment-classes/{cls['id']}", json={"code": uniq.class_code()})
        assert res.status_code == 409


def _types(client, query=""):
    return client.get(f"{BASE}/equipment-types{query}").get_json()["items"]


class TestEquipmentTypes:

    def test_create_list_rename(self, engineer, make_class):
        cls = make_class()
        created = engineer.post(f"{BASE}/equipment-types", json={"class_id": cls["id"], "name": " Closed execution "})
        assert created.status_code == 201
        record = created.get_json()
        assert (record["class_id"], record["class_code"], record["name"], record["active"]) == \
            (cls["id"], cls["code"], "Closed execution", 1)
        assert record["created_by"] == "test_maint_engineer" and record["updated_at"] is None

        renamed = engineer.put(f"{BASE}/equipment-types/{record['id']}", json={"name": "Closed exec."})
        assert renamed.status_code == 200
        assert renamed.get_json()["name"] == "Closed exec."
        assert renamed.get_json()["updated_by"] == "test_maint_engineer"

    def test_list_filters_by_class_and_is_ordered_by_class_code_then_name(self, engineer, make_class, make_type):
        cls, other = make_class(), make_class()
        open_ex = make_type(cls=cls, name="Open execution")
        closed_ex = make_type(cls=cls, name="Closed execution")
        elsewhere = make_type(cls=other)
        assert [t["id"] for t in _types(engineer, f"?class_id={cls['id']}")] == [closed_ex["id"], open_ex["id"]]
        listed = _types(engineer)
        assert {open_ex["id"], closed_ex["id"], elsewhere["id"]} <= {t["id"] for t in listed}
        assert listed == sorted(listed, key=lambda t: (t["class_code"], t["name"].lower()))

    @pytest.mark.parametrize("raw", ["x", "-1", "1.5", "²"])
    def test_bad_class_filter_is_400(self, engineer, raw):
        res = engineer.get(f"{BASE}/equipment-types?class_id={raw}")
        assert res.status_code == 400
        assert res.get_json()["field"] == "class_id"

    def test_deactivate_hides_unless_requested_and_reactivate(self, engineer, make_type):
        record = make_type()
        query = f"?class_id={record['class_id']}"
        assert engineer.put(f"{BASE}/equipment-types/{record['id']}", json={"active": False}).status_code == 200
        assert _types(engineer, query) == []
        assert [t["active"] for t in _types(engineer, f"{query}&include_inactive=1")] == [0]
        assert engineer.put(f"{BASE}/equipment-types/{record['id']}", json={"active": True}).status_code == 200
        assert [t["id"] for t in _types(engineer, query)] == [record["id"]]

    def test_duplicate_name_in_a_class_is_409_case_insensitive(self, engineer, make_class, make_type):
        cls = make_class()
        make_type(cls=cls, name="Closed execution")
        res = engineer.post(f"{BASE}/equipment-types", json={"class_id": cls["id"], "name": "closed EXECUTION"})
        assert res.status_code == 409
        assert res.get_json() == {"error": "A type with this name already exists in this class", "field": "name"}

    def test_rename_onto_a_sibling_is_409(self, engineer, make_class, make_type):
        cls = make_class()
        make_type(cls=cls, name="Closed execution")
        other = make_type(cls=cls, name="Open execution")
        res = engineer.put(f"{BASE}/equipment-types/{other['id']}", json={"name": "Closed execution"})
        assert res.status_code == 409 and res.get_json()["field"] == "name"

    def test_the_same_name_in_another_class_is_fine(self, make_type):
        first = make_type(name="Standard")
        second = make_type(name="Standard")
        assert first["class_id"] != second["class_id"]

    def test_the_name_none_is_reserved(self, engineer, make_class):
        res = engineer.post(f"{BASE}/equipment-types", json={"class_id": make_class()["id"], "name": "None"})
        assert res.status_code == 400 and res.get_json()["field"] == "name"

    def test_unknown_class_on_create_is_400(self, engineer):
        res = engineer.post(f"{BASE}/equipment-types", json={"class_id": 999999, "name": "x"})
        assert res.status_code == 400
        assert res.get_json() == {"error": "Unknown class", "field": "class_id"}

    def test_inactive_class_on_create_is_409(self, engineer, make_class):
        cls = make_class()
        engineer.put(f"{BASE}/equipment-classes/{cls['id']}", json={"active": False})
        res = engineer.post(f"{BASE}/equipment-types", json={"class_id": cls["id"], "name": "x"})
        assert res.status_code == 409
        assert res.get_json() == {"error": "The class is inactive", "field": "class_id"}

    def test_reactivating_under_an_inactive_class_is_409(self, engineer, make_class, make_type):
        cls = make_class()
        record = make_type(cls=cls)
        engineer.put(f"{BASE}/equipment-types/{record['id']}", json={"active": False})
        engineer.put(f"{BASE}/equipment-classes/{cls['id']}", json={"active": False})
        res = engineer.put(f"{BASE}/equipment-types/{record['id']}", json={"active": True})
        assert res.status_code == 409
        assert res.get_json() == {"error": "The class is inactive", "field": "active"}
        # Renaming it is still fine: only reactivation needs an active class
        assert engineer.put(f"{BASE}/equipment-types/{record['id']}", json={"name": "Renamed"}).status_code == 200

    def test_deactivating_a_type_in_use_is_allowed(self, engineer, make_type, make_equipment):
        record = make_type()
        make_equipment(cls={"id": record["class_id"]}, type_id=record["id"])
        assert engineer.put(f"{BASE}/equipment-types/{record['id']}", json={"active": False}).status_code == 200

    def test_class_cannot_change_but_may_be_sent_back(self, engineer, make_class, make_type):
        record = make_type()
        res = engineer.put(f"{BASE}/equipment-types/{record['id']}", json={"class_id": make_class()["id"]})
        assert res.status_code == 400
        assert res.get_json() == {"error": "Class cannot be changed", "field": "class_id"}
        same = engineer.put(f"{BASE}/equipment-types/{record['id']}",
                            json={"class_id": record["class_id"], "name": "Kept"})
        assert same.status_code == 200
        assert (same.get_json()["class_id"], same.get_json()["name"]) == (record["class_id"], "Kept")

    def test_unknown_type_is_404(self, engineer):
        assert engineer.put(f"{BASE}/equipment-types/999999", json={"name": "x"}).status_code == 404


class TestPermissions:

    @pytest.mark.parametrize("role", ["maint_operator", "maint_technician", "maint_storekeeper",
                                      "maint_engineer", "maint_manager", "it_admin", "admin"])
    def test_every_role_can_read_the_pick_lists(self, role_client, role):
        client = role_client(role)
        for path in ("sites", "units", "equipment-classes", "equipment-types"):
            assert client.get(f"{BASE}/{path}").status_code == 200, (role, path)

    def test_unknown_role_is_forbidden(self, role_client):
        assert role_client("nobody").get(f"{BASE}/sites").status_code == 403

    @pytest.mark.parametrize("role", ["maint_operator", "maint_technician", "maint_engineer", "maint_manager"])
    def test_only_it_admin_writes_sites_and_units(self, role_client, role):
        client = role_client(role)
        assert client.post(f"{BASE}/sites", json={"code": "XX", "name": "x"}).status_code == 403
        assert client.put(f"{BASE}/sites/1", json={"name": "x"}).status_code == 403
        assert client.post(f"{BASE}/units", json={"site_id": 1, "code": "XX", "name": "x"}).status_code == 403
        assert client.put(f"{BASE}/units/1", json={"name": "x"}).status_code == 403

    @pytest.mark.parametrize("role", ["maint_operator", "maint_technician", "maint_storekeeper"])
    def test_floor_roles_cannot_write_classes(self, role_client, role):
        client = role_client(role)
        assert client.post(f"{BASE}/equipment-classes", json={"code": "XX", "name": "x"}).status_code == 403
        assert client.put(f"{BASE}/equipment-classes/1", json={"name": "x"}).status_code == 403
        assert client.post(f"{BASE}/equipment-types", json={"class_id": 1, "name": "x"}).status_code == 403
        assert client.put(f"{BASE}/equipment-types/1", json={"name": "x"}).status_code == 403

    @pytest.mark.parametrize("role", ["maint_engineer", "maint_manager", "it_admin", "admin"])
    def test_class_writers(self, role_client, role, uniq):
        client = role_client(role)
        res = client.post(f"{BASE}/equipment-classes", json={"code": uniq.class_code(), "name": "x"})
        assert res.status_code == 201
        res = client.post(f"{BASE}/equipment-types", json={"class_id": res.get_json()["id"], "name": "x"})
        assert res.status_code == 201
        assert client.put(f"{BASE}/equipment-types/{res.get_json()['id']}", json={"name": "y"}).status_code == 200

    def test_user_units_routes_are_gone(self, admin):
        """S011 A1: access lives on the person (Team); /user-units is removed."""
        assert admin.get(f"{BASE}/user-units").status_code == 404
        assert admin.put(f"{BASE}/user-units/someone", json={"unit_ids": []}).status_code == 404


def _default_ids(admin):
    items = admin.get(f"{BASE}/sites?include_inactive=1").get_json()["items"]
    return [s["id"] for s in items if s["is_default"]]


class TestDefaultSite:

    def test_set_a_default_and_see_it_in_the_list(self, admin, make_site):
        site = make_site()
        assert site["is_default"] is False
        res = admin.put(f"{BASE}/sites/{site['id']}", json={"is_default": True})
        assert res.status_code == 200
        assert res.get_json()["is_default"] is True
        assert _default_ids(admin) == [site["id"]]

    def test_moving_the_default_clears_the_old_one_and_audits_both(self, admin, make_site):
        site_a, site_b = make_site(), make_site()
        admin.put(f"{BASE}/sites/{site_a['id']}", json={"is_default": True})
        res = admin.put(f"{BASE}/sites/{site_b['id']}", json={"is_default": True})
        assert res.status_code == 200
        assert _default_ids(admin) == [site_b["id"]]
        old = _row("SELECT is_default, updated_by, updated_at FROM sites WHERE id = %s", (site_a["id"],))
        assert old["is_default"] is None  # NULL, never 0
        assert old["updated_by"] == "test_it_admin" and old["updated_at"]
        assert res.get_json()["updated_by"] == "test_it_admin"

    def test_unticking_leaves_no_default(self, admin, make_site):
        site = make_site()
        admin.put(f"{BASE}/sites/{site['id']}", json={"is_default": True})
        res = admin.put(f"{BASE}/sites/{site['id']}", json={"is_default": False})
        assert res.get_json()["is_default"] is False
        assert _default_ids(admin) == []
        assert _row("SELECT is_default FROM sites WHERE id = %s", (site["id"],))["is_default"] is None

    def test_creating_a_default_site_moves_the_default(self, admin, make_site):
        old = make_site(is_default=True)
        new = make_site(is_default=True)
        assert new["is_default"] is True
        assert _default_ids(admin) == [new["id"]]
        assert old["id"] not in _default_ids(admin)

    def test_inactive_site_cannot_become_the_default(self, admin, make_site):
        site = make_site()
        admin.put(f"{BASE}/sites/{site['id']}", json={"active": False})
        res = admin.put(f"{BASE}/sites/{site['id']}", json={"is_default": True})
        assert res.status_code == 409
        assert res.get_json()["field"] == "is_default"

    def test_inactive_site_cannot_be_created_as_the_default(self, admin, uniq):
        res = admin.post(f"{BASE}/sites", json={"code": uniq.site_code(), "name": "x",
                                                "active": False, "is_default": True})
        assert res.status_code == 409

    def test_default_site_cannot_be_deactivated(self, admin, make_site):
        site = make_site()
        admin.put(f"{BASE}/sites/{site['id']}", json={"is_default": True})
        res = admin.put(f"{BASE}/sites/{site['id']}", json={"active": False})
        assert res.status_code == 409
        assert res.get_json()["field"] == "active"
        assert "default" in res.get_json()["error"]
        assert admin.put(f"{BASE}/sites/{site['id']}", json={"is_default": False}).status_code == 200
        assert admin.put(f"{BASE}/sites/{site['id']}", json={"active": False}).status_code == 200

    def test_a_failed_move_changes_nothing(self, admin, make_site):
        old, inactive = make_site(), make_site()
        admin.put(f"{BASE}/sites/{old['id']}", json={"is_default": True})
        admin.put(f"{BASE}/sites/{inactive['id']}", json={"active": False})
        admin.put(f"{BASE}/sites/{inactive['id']}", json={"is_default": True})
        assert _default_ids(admin) == [old["id"]]

    def test_the_database_allows_only_one_default(self, make_site):
        first, second = make_site(), make_site()
        conn = get_local_db(config.DB_CONFIG)
        try:
            with conn.cursor() as cur:
                cur.execute("UPDATE sites SET is_default = NULL WHERE is_default = 1")
                cur.execute("UPDATE sites SET is_default = 1 WHERE id = %s", (first["id"],))
                with pytest.raises(pymysql.err.IntegrityError, match="uq_sites_default"):
                    cur.execute("UPDATE sites SET is_default = 1 WHERE id = %s", (second["id"],))
                cur.execute("UPDATE sites SET is_default = NULL WHERE is_default = 1")
        finally:
            conn.close()

    def test_deactivating_a_non_default_site_while_ticking_default(self, admin, make_site):
        site = make_site()
        res = admin.put(f"{BASE}/sites/{site['id']}", json={"active": False, "is_default": True})
        assert res.status_code == 409
        assert res.get_json()["field"] == "is_default"
        assert "cannot be the default" in res.get_json()["error"]

    def test_unique_index_violation_maps_to_409(self, admin, make_site, monkeypatch):
        # Two racing saves: skip the clearing step so the index is what stops the second one
        import masters
        monkeypatch.setattr(masters, "_clear_default_site", lambda cur, except_id=None: None)
        first, second = make_site(), make_site()
        admin.put(f"{BASE}/sites/{first['id']}", json={"is_default": True})
        res = admin.put(f"{BASE}/sites/{second['id']}", json={"is_default": True})
        assert res.status_code == 409
        assert res.get_json()["field"] == "is_default"
        assert "same time" in res.get_json()["error"]

    def test_engineer_cannot_set_the_default(self, engineer, make_site):
        site = make_site()
        res = engineer.put(f"{BASE}/sites/{site['id']}", json={"is_default": True})
        assert res.status_code == 403
        assert engineer.post(f"{BASE}/sites", json={"code": "XX", "name": "x", "is_default": True}).status_code == 403


class TestErrorMapping:
    """The failure branches of the database-error mapping, and 503 when the DB is down."""

    def test_a_foreign_key_error_is_not_a_409(self, admin, uniq, monkeypatch):
        import masters

        def fail(cur, table, clean, actor):
            raise pymysql.err.IntegrityError(1452, "Cannot add or update a child row")
        monkeypatch.setattr(masters, "insert_row", fail)
        # TESTING=True makes Flask re-raise unhandled errors; in production this is a logged 500
        with pytest.raises(pymysql.err.IntegrityError):
            admin.post(f"{BASE}/sites", json={"code": uniq.site_code(), "name": "x"})

    def test_a_duplicate_on_an_unmapped_key_is_a_generic_409(self, admin, uniq, monkeypatch):
        import masters

        def fail(cur, table, clean, actor):
            raise pymysql.err.IntegrityError(1062, "Duplicate entry 'x' for key 'PRIMARY'")
        monkeypatch.setattr(masters, "insert_row", fail)
        res = admin.post(f"{BASE}/sites", json={"code": uniq.site_code(), "name": "x"})
        assert res.status_code == 409
        assert "field" not in res.get_json()
        assert "Conflicts" in res.get_json()["error"]

    def test_the_key_name_is_read_from_the_end_of_the_message(self, admin, uniq, monkeypatch):
        import masters

        def fail(cur, table, clean, actor):
            raise pymysql.err.IntegrityError(
                1062, "Duplicate entry 'x' for key 'uq_sites_code' for key 'PRIMARY'")
        monkeypatch.setattr(masters, "insert_row", fail)
        res = admin.post(f"{BASE}/sites", json={"code": uniq.site_code(), "name": "x"})
        assert res.status_code == 409
        assert "field" not in res.get_json()

    def test_a_masters_route_is_503_when_the_database_is_unavailable(self, admin, monkeypatch):
        import db_helpers
        monkeypatch.setattr(db_helpers, "ensure_schema", lambda cfg: "down")
        assert admin.get(f"{BASE}/sites").status_code == 503

    def test_no_connection_is_503_not_500(self, admin, monkeypatch):
        import db_helpers

        def refuse():
            raise pymysql.err.OperationalError(2003, "Can't connect to MySQL server")
        monkeypatch.setattr(db_helpers, "get_pooled_db", refuse)
        res = admin.get(f"{BASE}/sites")
        assert res.status_code == 503
        assert "Database unavailable" in res.get_json()["error"]
