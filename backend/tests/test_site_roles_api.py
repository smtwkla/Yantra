"""Site roles of people (S011 amendment A1 and the gate-A decisions), against the test DB.

A person's role per site, with all the site's units or chosen ones.  IT admin sets any role
(a login save carries the whole set; per-site routes otherwise); an engineer assigns
Technicians at their own site.  The per-site cases run as maintenance_team users with real
memberships (user_at_sites): the X-Test-Role wildcard would hide "at B -> 403".

Needs the dev MariaDB container (tooling/dev/dev-db-up.bat).
"""

import logging

import pytest

import config
from local_db import get_local_db

BASE = "/api/masters"
EQUIPMENT = "/api/equipment"


def _row(**kw):
    return {"role": "maint_technician", "all_units": False, "unit_ids": [], **kw}


def _site(site, role="maint_technician", units="all"):
    return {"site_id": site["id"], "role": role, "all_units": units == "all",
            "unit_ids": [] if units == "all" else [u["id"] for u in units]}


def _person(client, person_id):
    items = client.get(f"{BASE}/people?include_inactive=1").get_json()["items"]
    return next(i for i in items if i["id"] == person_id)


def _sites(client, person_id):
    return {s["site_id"]: s for s in _person(client, person_id)["sites"]}


@pytest.fixture
def two_sites(make_site, make_unit):
    """Sites A and B with two units each: (site_a, [a1, a2], site_b, [b1, b2])."""
    site_a, site_b = make_site(), make_site()
    return site_a, [make_unit(site_a), make_unit(site_a)], site_b, [make_unit(site_b), make_unit(site_b)]


@pytest.fixture
def engineer_at_a(user_at_sites, two_sites):
    """An engineer at A (all units) who is an operator at B: (client, own person)."""
    site_a, _, site_b, _ = two_sites
    return user_at_sites([(site_a, "maint_engineer", "all"), (site_b, "maint_operator", "all")])


class TestLoginSave:
    """A1 rule 1: setting, changing or clearing a login carries the whole set of sites."""

    def test_set_login_with_two_sites_and_read_back(self, admin, make_person, uniq, two_sites):
        site_a, _, site_b, units_b = two_sites
        person = make_person(username=uniq.username(),
                             sites=[_site(site_a, "maint_manager"), _site(site_b, "maint_operator", [units_b[0]])])
        rows = _sites(admin, person["id"])
        assert rows[site_a["id"]]["role"] == "maint_manager" and rows[site_a["id"]]["all_units"] is True
        assert rows[site_a["id"]]["units"] == []
        assert rows[site_b["id"]]["role"] == "maint_operator"
        assert [u["id"] for u in rows[site_b["id"]]["units"]] == [units_b[0]["id"]]
        assert set(rows[site_b["id"]]["units"][0]) == {"id", "full_code", "name", "active"}
        assert rows[site_a["id"]]["site_code"] == site_a["code"] and rows[site_a["id"]]["active"] is True

    def test_login_change_without_sites_is_400(self, admin, make_person, uniq):
        person = make_person()
        res = admin.put(f"{BASE}/people/{person['id']}", json={"username": uniq.username()})
        assert (res.status_code, res.get_json()["field"]) == (400, "sites")
        res = admin.post(f"{BASE}/people", json={"name": "x", "employment": "direct", "username": uniq.username()})
        assert (res.status_code, res.get_json()["field"]) == (400, "sites")

    def test_sites_without_a_login_change_are_400(self, admin, make_person, two_sites):
        person = make_person()
        res = admin.put(f"{BASE}/people/{person['id']}", json={"name": "x", "sites": [_site(two_sites[0])]})
        assert (res.status_code, res.get_json()["field"]) == (400, "sites")

    @pytest.mark.parametrize("sites, field", [
        ("x", "sites"), ([1], "sites"), ([{"site_id": "1", "role": "maint_operator", "all_units": True}], "site_id"),
        ([{"site_id": 99999999, "role": "maint_operator", "all_units": True}], "sites"),
        ([{"site_id": "A", "role": "maint_operator", "all_units": True}], "site_id"),
    ])
    def test_body_shape(self, admin, make_person, uniq, sites, field):
        person = make_person()
        res = admin.put(f"{BASE}/people/{person['id']}", json={"username": uniq.username(), "sites": sites})
        assert (res.status_code, res.get_json()["field"]) == (400, field)

    def test_row_rules(self, admin, make_person, uniq, two_sites):
        site_a, units_a, site_b, units_b = two_sites
        person = make_person()

        def put(*sites):
            return admin.put(f"{BASE}/people/{person['id']}", json={"username": uniq.username(), "sites": list(sites)})

        cases = [
            ({**_site(site_a), "unit_ids": [units_a[0]["id"]]}, "unit_ids"),         # all units and units
            (_site(site_a, units=[units_b[0]]), "unit_ids"),                         # a unit of another site
            ({"site_id": site_a["id"], "role": "maint_boss", "all_units": True}, "role"),
            ({"site_id": site_a["id"], "all_units": True}, "role"),                  # no role
            ({"site_id": site_a["id"], "role": "it_admin", "all_units": True}, "role"),
            ({"site_id": site_a["id"], "role": "maint_operator", "all_units": False}, "unit_ids"),
        ]
        for row, field in cases:
            res = put(row)
            assert (res.status_code, res.get_json()["field"]) == (400, field), row
        res = put(_site(site_a), _site(site_a, "maint_operator"))
        assert (res.status_code, res.get_json()["field"]) == (400, "sites")
        assert put({"site_id": site_a["id"], "all_units": True}).get_json()["error"] == "Choose a role"
        assert _person(admin, person["id"])["username"] is None   # nothing was written

    def test_inactive_site_not_newly_granted_but_kept(self, admin, make_person, make_site, uniq):
        site = make_site()
        res = admin.put(f"{BASE}/sites/{site['id']}", json={"active": 0})
        assert res.status_code == 200
        person = make_person()
        res = admin.put(f"{BASE}/people/{person['id']}", json={"username": uniq.username(), "sites": [_site(site)]})
        assert (res.status_code, res.get_json()["field"]) == (400, "sites")

        kept_site = make_site()
        login = uniq.username()
        held = make_person(username=login, sites=[_site(kept_site)])
        admin.put(f"{BASE}/sites/{kept_site['id']}", json={"active": 0})
        res = admin.put(f"{BASE}/people/{held['id']}", json={"username": uniq.username(), "sites": [_site(kept_site)]})
        assert res.status_code == 200, res.get_json()
        assert _sites(admin, held["id"])[kept_site["id"]]["active"] is False

    def test_inactive_unit_not_newly_granted_but_kept(self, admin, make_person, uniq, two_sites):
        site_a, (kept, other), _, _ = two_sites
        person = make_person(username=uniq.username(), sites=[_site(site_a, "maint_operator", [kept])])
        admin.put(f"{BASE}/units/{kept['id']}", json={"active": False})
        admin.put(f"{BASE}/units/{other['id']}", json={"active": False})
        res = admin.put(f"{BASE}/people/{person['id']}/sites/{site_a['id']}",
                        json=_row(role="maint_operator", unit_ids=[kept["id"], other["id"]]))
        assert (res.status_code, res.get_json()["field"]) == (400, "unit_ids")
        res = admin.put(f"{BASE}/people/{person['id']}/sites/{site_a['id']}",
                        json=_row(role="maint_engineer", unit_ids=[kept["id"]]))
        assert res.status_code == 200
        admin.put(f"{BASE}/units/{other['id']}", json={"active": True})

    def test_switching_to_all_units_removes_the_unit_rows(self, admin, db_rows, make_person, uniq, two_sites):
        site_a, units_a, _, _ = two_sites
        person = make_person(username=uniq.username(), sites=[_site(site_a, "maint_operator", units_a)])
        assert len(db_rows("SELECT unit_id FROM person_units WHERE person_id = %s", (person["id"],))) == 2
        res = admin.put(f"{BASE}/people/{person['id']}/sites/{site_a['id']}", json=_row(role="maint_operator",
                                                                                      all_units=True))
        assert res.status_code == 200
        assert db_rows("SELECT unit_id FROM person_units WHERE person_id = %s", (person["id"],)) == ()
        assert _sites(admin, person["id"])[site_a["id"]]["all_units"] is True

    def test_an_empty_list_removes_every_site(self, admin, db_rows, make_person, uniq, two_sites):
        site_a, units_a, site_b, _ = two_sites
        person = make_person(username=uniq.username(), sites=[_site(site_a, "maint_operator", units_a), _site(site_b)])
        res = admin.put(f"{BASE}/people/{person['id']}", json={"username": uniq.username(), "sites": []})
        assert res.status_code == 200 and res.get_json()["sites"] == []
        assert db_rows("SELECT site_id FROM memberships WHERE person_id = %s", (person["id"],)) == ()
        assert db_rows("SELECT unit_id FROM person_units WHERE person_id = %s", (person["id"],)) == ()

    def test_whole_set_replaces_an_engineers_earlier_row(self, admin, engineer_at_a, make_person, uniq,
                                                         two_sites):
        site_a, _, site_b, _ = two_sites
        engineer, _ = engineer_at_a
        person = make_person()
        assert engineer.put(f"{BASE}/people/{person['id']}/sites/{site_a['id']}",
                            json=_row(all_units=True)).status_code == 200
        res = admin.put(f"{BASE}/people/{person['id']}",
                        json={"username": uniq.username(), "sites": [_site(site_b, "maint_manager")]})
        assert res.status_code == 200
        assert set(_sites(admin, person["id"])) == {site_b["id"]}

    def test_login_save_is_logged_once(self, admin, make_person, uniq, two_sites, caplog):
        site_a = two_sites[0]
        person = make_person()
        login = uniq.username()
        with caplog.at_level(logging.INFO, logger="masters"):
            admin.put(f"{BASE}/people/{person['id']}",
                      json={"username": login, "sites": [_site(site_a, "maint_manager")]})
        lines = [r.getMessage() for r in caplog.records if r.getMessage().startswith("login saved")]
        assert lines == [f"login saved: actor=test_it_admin person={person['id']} 'Test person' login=-->{login} "
                         f"before=[] after=[{site_a['code']}:maint_manager:all]"]

    def test_login_change_and_clear_log_both_sides(self, admin, make_person, uniq, two_sites, caplog):
        site_a, _, site_b, _ = two_sites
        old, new = uniq.username(), uniq.username()
        person = make_person(username=old, sites=[_site(site_a, "maint_manager"), _site(site_b)])
        with caplog.at_level(logging.INFO, logger="masters"):
            admin.put(f"{BASE}/people/{person['id']}", json={"username": new, "sites": [_site(site_a, "maint_manager")]})
            admin.put(f"{BASE}/people/{person['id']}", json={"username": None, "sites": [_site(site_a)]})
        lines = [r.getMessage() for r in caplog.records if r.getMessage().startswith("login saved")]
        prefix = f"login saved: actor=test_it_admin person={person['id']} 'Test person' login="
        codes = sorted([site_a["code"], site_b["code"]])
        before_both = ";".join(f"{c}:{'maint_manager' if c == site_a['code'] else 'maint_technician'}:all" for c in codes)
        assert lines[1:] == [f"{prefix}{old}->{new} before=[{before_both}] after=[{site_a['code']}:maint_manager:all]",
                         f"{prefix}{new}->- before=[{site_a['code']}:maint_manager:all] after=[{site_a['code']}:maint_technician:all]"]

    def test_rows_replaced_with_the_login_unchanged_or_absent_are_logged(self, admin, make_person, uniq, two_sites,
                                                                         caplog):
        site_a = two_sites[0]
        login = uniq.username()
        person = make_person(username=login, sites=[_site(site_a)])
        with caplog.at_level(logging.INFO, logger="masters"):
            admin.put(f"{BASE}/people/{person['id']}", json={"username": login, "sites": [_site(site_a, "maint_manager")]})
            res = admin.post(f"{BASE}/people", json={"name": "N", "employment": "direct", "username": None,
                                                      "sites": [_site(site_a)]})
        assert res.status_code == 201
        lines = [r.getMessage() for r in caplog.records if r.getMessage().startswith("login saved")][1:]
        code = site_a["code"]
        assert lines == [
            f"login saved: actor=test_it_admin person={person['id']} 'Test person' login={login}->{login} "
            f"before=[{code}:maint_technician:all] after=[{code}:maint_manager:all]",
            f"login saved: actor=test_it_admin person={res.get_json()['id']} 'N' login=-->- "
            f"before=[] after=[{code}:maint_technician:all]"]

    def test_unknown_unit_id_is_400_on_both_routes(self, admin, make_person, uniq, two_sites):
        site_a = two_sites[0]
        person = make_person()
        res = admin.put(f"{BASE}/people/{person['id']}",
                        json={"username": uniq.username(),
                              "sites": [{"site_id": site_a["id"], "role": "maint_operator",
                                         "all_units": False, "unit_ids": [99999999]}]})
        assert (res.status_code, res.get_json()["field"]) == (400, "unit_ids")
        res = admin.put(f"{BASE}/people/{person['id']}/sites/{site_a['id']}",
                        json=_row(unit_ids=[99999999]))
        assert (res.status_code, res.get_json()["field"]) == (400, "unit_ids")
        assert _person(admin, person["id"])["username"] is None and _sites(admin, person["id"]) == {}

    def test_whole_set_with_a_failing_second_row_writes_nothing(self, admin, make_person, uniq, two_sites):
        site_a, units_a, site_b, units_b = two_sites
        old = uniq.username()
        person = make_person(username=old, sites=[_site(site_b, "maint_operator")])
        before = _sites(admin, person["id"])
        res = admin.put(f"{BASE}/people/{person['id']}",
                        json={"username": uniq.username(),
                              "sites": [_site(site_a, "maint_manager"),
                                        _site(site_b, "maint_operator", [units_a[0]])]})   # a unit of A
        assert (res.status_code, res.get_json()["field"]) == (400, "unit_ids")
        assert _person(admin, person["id"])["username"] == old
        assert _sites(admin, person["id"]) == before


class TestNoLoginTechnicianOnly:
    """Gate A: without a login a person can only be a technician — or, since S017 (user
    decision 5), an operator, set by IT admin only."""

    @pytest.mark.parametrize("role", ["maint_engineer", "maint_manager", "maint_supervisor"])
    def test_other_roles_are_400(self, admin, engineer_at_a, make_person, two_sites, role):
        site_a = two_sites[0]
        person = make_person()
        for client in (engineer_at_a[0], admin):
            res = client.put(f"{BASE}/people/{person['id']}/sites/{site_a['id']}", json=_row(role=role, all_units=True))
            assert (res.status_code, res.get_json()["field"]) == (400, "role")
            assert res.get_json()["error"] == "Without a login, a person can only be a technician or an operator"

    def test_operator_is_200_for_it_admin(self, admin, make_person, two_sites):
        site_a = two_sites[0]
        person = make_person()
        res = admin.put(f"{BASE}/people/{person['id']}/sites/{site_a['id']}",
                        json=_row(role="maint_operator", all_units=True))
        assert res.status_code == 200
        assert [s["role"] for s in res.get_json()["sites"]] == ["maint_operator"]

    def test_operator_is_403_for_an_engineer(self, engineer_at_a, make_person, two_sites):
        """Was 400 before S017 (the no-login check refused Operator first); now Operator passes
        it and the engineer's Technician-only rule answers."""
        site_a = two_sites[0]
        person = make_person()
        res = engineer_at_a[0].put(f"{BASE}/people/{person['id']}/sites/{site_a['id']}",
                                   json=_row(role="maint_operator", all_units=True))
        assert (res.status_code, res.get_json()["field"]) == (403, "role")
        assert res.get_json()["error"] == "Only IT admin can set this role"

    def test_technician_is_200(self, engineer_at_a, make_person, two_sites):
        site_a, units_a, _, _ = two_sites
        person = make_person()
        res = engineer_at_a[0].put(f"{BASE}/people/{person['id']}/sites/{site_a['id']}",
                                   json=_row(unit_ids=[units_a[0]["id"]]))
        assert res.status_code == 200
        assert [s["role"] for s in res.get_json()["sites"]] == ["maint_technician"]

    def test_clearing_a_managers_login_with_the_manager_row_is_400(self, admin, make_person, uniq, two_sites):
        site_a = two_sites[0]
        person = make_person(username=uniq.username(), sites=[_site(site_a, "maint_manager")])
        res = admin.put(f"{BASE}/people/{person['id']}",
                        json={"username": None, "sites": [_site(site_a, "maint_manager")]})
        assert (res.status_code, res.get_json()["field"]) == (400, "role")
        res = admin.put(f"{BASE}/people/{person['id']}", json={"username": None})
        assert (res.status_code, res.get_json()["field"]) == (400, "sites")
        res = admin.put(f"{BASE}/people/{person['id']}", json={"username": None, "sites": [_site(site_a)]})
        assert res.status_code == 200 and res.get_json()["has_login"] is False

    def test_create_without_login_with_a_manager_row_is_400(self, admin, two_sites):
        res = admin.post(f"{BASE}/people", json={"name": "x", "employment": "direct", "username": None,
                                                 "sites": [_site(two_sites[0], "maint_manager")]})
        assert (res.status_code, res.get_json()["field"]) == (400, "role")


class TestEngineerAssignsTechnicians:
    """Gate A: people:assign_technicians at the site, Technician rows only."""

    def test_adds_a_technician_with_a_login_who_then_works_at_a(self, admin, engineer_at_a, make_person,
                                                               make_equipment, role_client, uniq, two_sites):
        site_a, units_a, _, _ = two_sites
        mill = make_equipment(unit=units_a[0])
        login = uniq.username()
        person = make_person(username=login)
        technician = role_client("maintenance_team", login)
        assert technician.get(f"{EQUIPMENT}/{mill['id']}").status_code == 403
        res = engineer_at_a[0].put(f"{BASE}/people/{person['id']}/sites/{site_a['id']}",
                                   json=_row(unit_ids=[units_a[0]["id"]]))
        assert res.status_code == 200
        assert technician.get(f"{EQUIPMENT}/{mill['id']}").status_code == 200

    @pytest.mark.parametrize("has_login", [False, True])
    def test_at_b_is_403(self, engineer_at_a, make_person, uniq, two_sites, has_login):
        site_b = two_sites[2]
        person = make_person(username=uniq.username()) if has_login else make_person()
        res = engineer_at_a[0].put(f"{BASE}/people/{person['id']}/sites/{site_b['id']}", json=_row(all_units=True))
        assert res.status_code == 403
        assert res.get_json()["error"] == f"You can't do this at {site_b['code']}"

    def test_cannot_change_or_remove_an_operator_row(self, admin, engineer_at_a, make_person, uniq, two_sites):
        """Also the "locked check": IT admin's login save is committed, and the engineer's
        later write is decided on the stored row."""
        site_a = two_sites[0]
        person = make_person(username=uniq.username(), sites=[_site(site_a, "maint_operator")])
        engineer = engineer_at_a[0]
        res = engineer.put(f"{BASE}/people/{person['id']}/sites/{site_a['id']}", json=_row(all_units=True))
        assert (res.status_code, res.get_json()["error"]) == (403, "Only IT admin can set this role")
        assert engineer.delete(f"{BASE}/people/{person['id']}/sites/{site_a['id']}").status_code == 403
        assert _sites(admin, person["id"])[site_a["id"]]["role"] == "maint_operator"

    def test_cannot_give_supervisor(self, engineer_at_a, make_person, uniq, two_sites):
        person = make_person(username=uniq.username())
        res = engineer_at_a[0].put(f"{BASE}/people/{person['id']}/sites/{two_sites[0]['id']}",
                                   json=_row(role="maint_supervisor", all_units=True))
        assert (res.status_code, res.get_json()["field"]) == (403, "role")

    def test_units_any_of_the_site(self, user_at_sites, make_person, two_sites):
        """BR-A1G-03: the site is the boundary, not the engineer's own units."""
        site_a, (a1, a2), _, _ = two_sites
        engineer, _ = user_at_sites([(site_a, "maint_engineer", [a1])])
        person = make_person()
        res = engineer.put(f"{BASE}/people/{person['id']}/sites/{site_a['id']}", json=_row(unit_ids=[a2["id"]]))
        assert res.status_code == 200

    def test_rows_at_b_are_unchanged_by_a_save_at_a(self, admin, engineer_at_a, make_person, uniq, two_sites):
        site_a, units_a, site_b, units_b = two_sites
        person = make_person(username=uniq.username(), sites=[_site(site_b, "maint_operator", units_b)])
        before = _sites(admin, person["id"])[site_b["id"]]
        assert engineer_at_a[0].put(f"{BASE}/people/{person['id']}/sites/{site_a['id']}",
                                    json=_row(all_units=True)).status_code == 200
        assert _sites(admin, person["id"])[site_b["id"]] == before

    def test_change_and_remove_a_technician_row(self, admin, db_rows, engineer_at_a, make_person, two_sites):
        site_a, (a1, a2), _, _ = two_sites
        engineer = engineer_at_a[0]
        person = make_person()
        url = f"{BASE}/people/{person['id']}/sites/{site_a['id']}"
        assert engineer.put(url, json=_row(unit_ids=[a1["id"]])).status_code == 200
        granted = db_rows("SELECT granted_at, granted_by FROM memberships WHERE person_id = %s", (person["id"],))[0]
        assert engineer.put(url, json=_row(unit_ids=[a1["id"], a2["id"]])).status_code == 200
        assert db_rows("SELECT granted_at, granted_by FROM memberships WHERE person_id = %s",
                       (person["id"],))[0] == granted   # the diff keeps the first grant
        assert engineer.delete(url).status_code == 200
        assert engineer.delete(url).status_code == 404
        assert db_rows("SELECT unit_id FROM person_units WHERE person_id = %s", (person["id"],)) == ()

    def test_it_admin_sets_any_role(self, admin, make_person, uniq, two_sites):
        person = make_person(username=uniq.username())
        res = admin.put(f"{BASE}/people/{person['id']}/sites/{two_sites[0]['id']}",
                        json=_row(role="maint_manager", all_units=True))
        assert res.status_code == 200 and res.get_json()["sites"][0]["role"] == "maint_manager"

    @pytest.mark.parametrize("role", ["maint_operator", "maint_technician", "maint_supervisor", "maint_storekeeper"])
    def test_floor_roles_cannot(self, role_client, make_person, two_sites, role):
        person = make_person()
        url = f"{BASE}/people/{person['id']}/sites/{two_sites[0]['id']}"
        assert role_client(role).put(url, json=_row(all_units=True)).status_code == 403
        assert role_client(role).delete(url).status_code == 403

    def test_unknown_person_and_site(self, admin, make_person, two_sites):
        res = admin.put(f"{BASE}/people/99999999/sites/{two_sites[0]['id']}", json=_row(all_units=True))
        assert res.status_code == 404
        res = admin.put(f"{BASE}/people/{make_person()['id']}/sites/99999999", json=_row(all_units=True))
        assert (res.status_code, res.get_json()["field"]) == (400, "site_id")

    def test_bad_body_is_400_before_403(self, engineer_at_a, make_person, two_sites):
        res = engineer_at_a[0].put(f"{BASE}/people/{make_person()['id']}/sites/{two_sites[2]['id']}", json=[1])
        assert res.status_code == 400

    def test_change_is_logged_only_when_it_changes(self, engineer_at_a, make_person, two_sites, caplog):
        site_a, (a1, _), _, _ = two_sites
        person = make_person()
        url = f"{BASE}/people/{person['id']}/sites/{site_a['id']}"
        with caplog.at_level(logging.INFO, logger="masters"):
            engineer_at_a[0].put(url, json=_row(unit_ids=[a1["id"]]))
            engineer_at_a[0].put(url, json=_row(unit_ids=[a1["id"]]))
        lines = [r.getMessage() for r in caplog.records if r.getMessage().startswith("site role changed")]
        assert len(lines) == 1
        assert lines[0].endswith(f"site={site_a['code']} before=[-] "
                                 f"after=[{site_a['code']}:maint_technician:{a1['code']}]")


class TestOwnAccess:
    """§ 5.5, A1 rule 4: nobody changes their own access, whatever their role."""

    @pytest.mark.parametrize("acting_as", ["{login}", " {upper} "])
    def test_it_admin_on_own_person(self, role_client, make_person, uniq, two_sites, acting_as):
        login = uniq.username()
        person = make_person(username=login)
        me = role_client("it_admin", acting_as.format(login=login, upper=login.upper()).strip())
        url = f"{BASE}/people/{person['id']}"
        res = me.put(f"{url}/sites/{two_sites[0]['id']}", json=_row(role="maint_manager", all_units=True))
        assert (res.status_code, res.get_json()["error"]) == (403, "You can't change your own access")
        assert me.put(url, json={"active": 0}).status_code == 403
        assert me.put(url, json={"username": None, "sites": []}).status_code == 403
        # Another IT admin may
        other = role_client("it_admin", uniq.username())
        res = other.put(f"{url}/sites/{two_sites[0]['id']}", json=_row(role="maint_manager", all_units=True))
        assert res.status_code == 200

    def test_engineer_on_own_person(self, engineer_at_a, two_sites):
        engineer, me = engineer_at_a
        url = f"{BASE}/people/{me['id']}/sites/{two_sites[0]['id']}"
        assert engineer.put(url, json=_row(all_units=True)).status_code == 403
        assert engineer.delete(url).status_code == 403


class TestVisibility:
    """A1 rule 5 refined at gate A; BR-A1G-02 editable and assignable_site_ids."""

    def test_engineer_sees_rows_by_login_and_site(self, engineer_at_a, make_person, uniq, two_sites):
        site_a, _, site_b, _ = two_sites
        engineer = engineer_at_a[0]
        no_login = make_person()
        # Of a person with a login, only the rows at the engineer's site are visible
        from_admin = make_person(username=uniq.username(),
                                 sites=[_site(site_a, "maint_operator"), _site(site_b, "maint_operator")])
        engineer.put(f"{BASE}/people/{no_login['id']}/sites/{site_a['id']}", json=_row(all_units=True))

        seen = _person(engineer, from_admin["id"])
        assert "username" not in seen and seen["has_login"] is True
        assert [s["site_id"] for s in seen["sites"]] == [site_a["id"]]
        assert seen["sites"][0]["editable"] is False                 # an operator row

        mine = _person(engineer, no_login["id"])
        assert [s["site_id"] for s in mine["sites"]] == [site_a["id"]]
        assert mine["sites"][0]["editable"] is True
        assert site_b["id"] not in mine["assignable_site_ids"]
        assert site_a["id"] not in mine["assignable_site_ids"]       # already has a row there

    def test_no_login_rows_visible_at_every_site(self, admin, engineer_at_a, make_person, two_sites):
        site_a, _, site_b, _ = two_sites
        person = make_person()
        admin.put(f"{BASE}/people/{person['id']}/sites/{site_b['id']}", json=_row(all_units=True))
        row = _person(engineer_at_a[0], person["id"])
        assert [s["site_id"] for s in row["sites"]] == [site_b["id"]]
        assert row["sites"][0]["editable"] is False                  # B is not the engineer's site
        assert site_a["id"] in row["assignable_site_ids"]

    def test_it_admin_sees_all(self, admin, make_person, uniq, two_sites):
        site_a, _, site_b, _ = two_sites
        person = make_person(username=uniq.username(), sites=[_site(site_a, "maint_manager"), _site(site_b)])
        row = _person(admin, person["id"])
        assert {s["site_id"] for s in row["sites"]} == {site_a["id"], site_b["id"]}
        assert all(s["editable"] for s in row["sites"])

    @pytest.mark.parametrize("role", ["maint_operator", "maint_technician", "maint_supervisor"])
    def test_floor_roles_see_no_sites(self, role_client, make_person, role):
        row = _person(role_client(role), make_person()["id"])
        assert "sites" not in row and "assignable_site_ids" not in row

    def test_put_response_is_filtered(self, engineer_at_a, make_person, uniq, two_sites):
        site_a, _, site_b, _ = two_sites
        person = make_person(username=uniq.username(), sites=[_site(site_b, "maint_operator")])
        res = engineer_at_a[0].put(f"{BASE}/people/{person['id']}/sites/{site_a['id']}", json=_row(all_units=True))
        body = res.get_json()
        assert "username" not in body
        assert [s["site_id"] for s in body["sites"]] == [site_a["id"]]

    def test_legacy_unit_rows_show_with_no_role(self, admin, db_rows, make_person, uniq, two_sites):
        """Rows moved from user_units by migration v8 have no membership yet."""
        site_a, units_a, _, _ = two_sites
        person = make_person(username=uniq.username())
        conn = get_local_db(config.DB_CONFIG)
        try:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO person_units (person_id, unit_id, granted_by) VALUES (%s, %s, 'legacy')",
                            (person["id"], units_a[0]["id"]))
        finally:
            conn.close()
        row = _sites(admin, person["id"])[site_a["id"]]
        assert row["role"] is None and [u["id"] for u in row["units"]] == [units_a[0]["id"]]
        # The first save gives it a role
        res = admin.put(f"{BASE}/people/{person['id']}/sites/{site_a['id']}",
                        json=_row(role="maint_operator", unit_ids=[units_a[0]["id"]]))
        assert res.status_code == 200
        assert _sites(admin, person["id"])[site_a["id"]]["role"] == "maint_operator"
