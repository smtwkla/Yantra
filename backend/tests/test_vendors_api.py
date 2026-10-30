"""Vendors (S079 § 5.1, § 5.4, § 6) — the masters API, against the test DB.  Needs the dev MariaDB container
(tooling/dev/dev-db-up.bat).  Each test makes its own vendors with names from ``uniq``; phone values are
obviously fake, never a real number."""

import pytest

from auth_utils import FORBIDDEN_TEXT
from masters_core import PHONE_RULE

BASE = "/api/masters"
VENDORS = f"{BASE}/vendors"
PHONE = "+91 00000 00000"

DUPLICATE = "A vendor with this name exists. Use that one, or enter a different name."
READERS_WITHOUT_EDIT = ["maint_operator", "maint_technician", "maint_supervisor", "maint_storekeeper"]
EDITORS = ["maint_engineer", "maint_manager"]


def _items(res):
    assert res.status_code == 200, res.get_json()
    return res.get_json()["items"]


def _listed(client, vendor_id, inactive=True):
    query = "?include_inactive=1" if inactive else ""
    return next((v for v in _items(client.get(f"{VENDORS}{query}")) if v["id"] == vendor_id), None)


class TestVendors:

    def test_create_list_and_edit(self, engineer, uniq):
        name = uniq.vendor_name()
        res = engineer.post(VENDORS, json={"name": f"  {name.replace(' ', '   ')} ", "phone": f" {PHONE} ",
                                           "note": " Screw compressors, MCC2 "})
        assert res.status_code == 201, res.get_json()
        vendor = res.get_json()
        assert {k: vendor[k] for k in ("name", "phone", "note", "active", "people_count", "created_by",
                                        "updated_at", "updated_by")} == {
            "name": name, "phone": PHONE, "note": "Screw compressors, MCC2", "active": 1, "people_count": 0,
            "created_by": "test_maint_engineer", "updated_at": None, "updated_by": None}
        assert vendor["created_at"]
        assert _listed(engineer, vendor["id"], inactive=False) == vendor
        edited = engineer.put(f"{VENDORS}/{vendor['id']}", json={"name": f"{name} Ltd", "note": "UPS"})
        assert edited.status_code == 200
        assert {k: edited.get_json()[k] for k in ("name", "phone", "note", "updated_by")} == {
            "name": f"{name} Ltd", "phone": PHONE, "note": "UPS", "updated_by": "test_maint_engineer"}

    def test_duplicate_by_case_or_by_repeated_spaces_is_409(self, engineer, uniq):
        name = f"Atlas Copco {uniq.vendor_name()}"
        assert engineer.post(VENDORS, json={"name": name}).status_code == 201
        for twin in (name.lower(), name.replace(" ", "   ")):
            res = engineer.post(VENDORS, json={"name": twin})
            assert (res.status_code, res.get_json()) == (409, {"error": DUPLICATE, "field": "name"})

    def test_listed_by_name_and_inactive_on_request(self, engineer, make_vendor, uniq):
        b = make_vendor(name=f"Zb {uniq.vendor_name()}")
        a = make_vendor(name=f"Za {uniq.vendor_name()}")
        listed = [v["id"] for v in _items(engineer.get(VENDORS))]
        assert listed.index(a["id"]) < listed.index(b["id"])
        assert engineer.put(f"{VENDORS}/{a['id']}", json={"active": False}).status_code == 200
        assert _listed(engineer, a["id"], inactive=False) is None
        assert _listed(engineer, a["id"])["active"] == 0

    @pytest.mark.parametrize("body, field, message", [
        ({}, "name", "Name is required"),
        ({"name": ""}, "name", "Name is required"),
        ({"name": "x" * 101}, "name", "Name must be at most 100 characters"),
        ({"name": 5}, "name", "Name is required"),
        ({"name": "V", "phone": 5}, "phone", "Phone must be text"),
        ({"name": "V", "phone": "0" * 21}, "phone", "Phone must be at most 20 characters"),
        ({"name": "V", "phone": "00000"}, "phone", PHONE_RULE),
        ({"name": "V", "phone": "0000000000000000"}, "phone", PHONE_RULE),
        ({"name": "V", "phone": "00 00+"}, "phone", PHONE_RULE),
        ({"name": "V", "phone": "0000 0000 ext"}, "phone", PHONE_RULE),
        ({"name": "V", "phone": "call 000000"}, "phone", PHONE_RULE),
        ({"name": "V", "note": "x" * 256}, "note", "Note must be at most 255 characters"),
        ({"name": "V", "note": []}, "note", "Note must be text"),
        ({"name": "V", "active": "yes"}, "active", "Active must be true or false"),
    ])
    def test_bad_input_is_400(self, engineer, body, field, message):
        res = engineer.post(VENDORS, json=body)
        assert (res.status_code, res.get_json()) == (400, {"error": message, "field": field})

    def test_a_body_that_is_not_an_object_is_400(self, engineer):
        res = engineer.post(VENDORS, json=[])
        assert (res.status_code, res.get_json()["error"]) == (400, "Request body must be a JSON object")

    def test_put_without_a_field_keeps_it_and_null_or_empty_clears_phone_and_note(self, engineer, make_vendor):
        vendor = make_vendor(phone=PHONE, note="UPS")
        unchanged = engineer.put(f"{VENDORS}/{vendor['id']}", json={})
        assert unchanged.status_code == 200 and unchanged.get_json() == vendor
        kept = engineer.put(f"{VENDORS}/{vendor['id']}", json={"name": vendor["name"]}).get_json()
        assert (kept["phone"], kept["note"]) == (PHONE, "UPS")
        cleared = engineer.put(f"{VENDORS}/{vendor['id']}", json={"phone": None, "note": ""}).get_json()
        assert (cleared["phone"], cleared["note"]) == (None, None)
        engineer.put(f"{VENDORS}/{vendor['id']}", json={"phone": PHONE, "note": "UPS"})
        cleared = engineer.put(f"{VENDORS}/{vendor['id']}", json={"phone": "  ", "note": None}).get_json()
        assert (cleared["phone"], cleared["note"]) == (None, None)

    def test_unknown_is_404(self, engineer):
        res = engineer.put(f"{VENDORS}/999999", json={"name": "x"})
        assert (res.status_code, res.get_json()) == (404, {"error": "Not found"})

    def test_deactivating_with_linked_people_is_allowed_and_links_stay(self, engineer, admin, make_vendor,
                                                                       make_person):
        vendor = make_vendor()
        person = make_person(employment="contractor", vendor_id=vendor["id"])
        res = engineer.put(f"{VENDORS}/{vendor['id']}", json={"active": False})
        assert (res.status_code, res.get_json()["active"], res.get_json()["people_count"]) == (200, 0, 1)
        row = next(p for p in _items(admin.get(f"{BASE}/people")) if p["id"] == person["id"])
        assert (row["vendor_id"], row["vendor_active"]) == (vendor["id"], False)
        assert engineer.put(f"{VENDORS}/{vendor['id']}", json={"active": True}).get_json()["active"] == 1

    def test_people_count_counts_active_linked_people_only(self, engineer, make_vendor, make_person):
        vendor = make_vendor()
        make_person(employment="contractor", vendor_id=vendor["id"])
        make_person(employment="contractor", vendor_id=vendor["id"], active=0)
        make_person(employment="contractor")
        assert _listed(engineer, vendor["id"])["people_count"] == 1


class TestPhoneReaders:

    @pytest.mark.parametrize("role, sees", [
        *[(role, False) for role in READERS_WITHOUT_EDIT],
        ("maint_engineer", True), ("maint_manager", True), ("it_admin", True),
    ])
    def test_phone_only_for_equipment_edit_holders(self, role_client, make_vendor, role, sees):
        vendor = make_vendor(phone=PHONE)
        listed = _listed(role_client(role), vendor["id"])
        assert listed["name"] == vendor["name"]
        assert ("phone" in listed) is sees
        if sees:
            assert listed["phone"] == PHONE


class TestPermissions:

    @pytest.mark.parametrize("role", [*READERS_WITHOUT_EDIT, *EDITORS, "it_admin"])
    def test_every_role_reads_the_list(self, role_client, make_vendor, role):
        vendor = make_vendor()
        assert _listed(role_client(role), vendor["id"]) is not None

    @pytest.mark.parametrize("role", READERS_WITHOUT_EDIT)
    def test_only_equipment_edit_holders_write(self, role_client, make_vendor, uniq, role):
        vendor = make_vendor()
        client = role_client(role)
        for res in (client.post(VENDORS, json={"name": uniq.vendor_name()}),
                    client.put(f"{VENDORS}/{vendor['id']}", json={"note": "x"})):
            assert (res.status_code, res.get_json()["error"]) == (403, FORBIDDEN_TEXT)

    @pytest.mark.parametrize("role", EDITORS)
    def test_editors_write(self, role_client, uniq, role):
        assert role_client(role).post(VENDORS, json={"name": uniq.vendor_name()}).status_code == 201

    def test_the_list_is_503_while_the_database_is_down(self, admin, db_down):
        assert admin.get(VENDORS).status_code == 503
        assert admin.post(VENDORS, json={"name": "Vendor down"}).status_code == 503
