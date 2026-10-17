"""Trades and the Team register of people API (S010, amendment A1), against the test DB.

Needs the dev MariaDB container (tooling/dev/dev-db-up.bat).
"""

import pytest

BASE = "/api/masters"

EDITORS = ["maint_engineer", "maint_manager"]   # people:edit without masters:edit


def _ids(items):
    return {i["id"] for i in items}


def _row(client, person_id):
    items = client.get(f"{BASE}/people?include_inactive=1").get_json()["items"]
    return next(i for i in items if i["id"] == person_id)


class TestTrades:

    def test_create_list_rename(self, admin, uniq):
        name = uniq.trade_name()
        created = admin.post(f"{BASE}/trades", json={"name": f" {name} "})
        assert created.status_code == 201
        trade = created.get_json()
        assert trade["name"] == name and trade["active"] == 1 and trade["created_by"] == "test_it_admin"
        assert trade["id"] in _ids(admin.get(f"{BASE}/trades").get_json()["items"])

        renamed = admin.put(f"{BASE}/trades/{trade['id']}", json={"name": f"{name} B"})
        assert renamed.status_code == 200
        assert renamed.get_json()["name"] == f"{name} B"
        assert renamed.get_json()["updated_by"] == "test_it_admin"

    def test_duplicate_name_in_another_case_is_409(self, admin, make_trade):
        trade = make_trade()
        res = admin.post(f"{BASE}/trades", json={"name": trade["name"].upper()})
        assert res.status_code == 409
        assert res.get_json()["field"] == "name"

    def test_inactive_hidden_unless_asked_and_reactivated(self, admin, make_trade):
        trade = make_trade()
        assert admin.put(f"{BASE}/trades/{trade['id']}", json={"active": 0}).get_json()["active"] == 0
        assert trade["id"] not in _ids(admin.get(f"{BASE}/trades").get_json()["items"])
        assert trade["id"] in _ids(admin.get(f"{BASE}/trades?include_inactive=1").get_json()["items"])
        assert admin.put(f"{BASE}/trades/{trade['id']}", json={"active": 1}).get_json()["active"] == 1
        assert trade["id"] in _ids(admin.get(f"{BASE}/trades").get_json()["items"])

    def test_invalid_name_and_unknown_id(self, admin):
        res = admin.post(f"{BASE}/trades", json={"name": "x" * 51})
        assert res.status_code == 400 and res.get_json()["field"] == "name"
        assert admin.put(f"{BASE}/trades/99999999", json={"name": "x"}).status_code == 404


class TestPeople:

    def test_create_with_two_trades_ordered_by_name(self, admin, uniq, make_trade):
        late, early = make_trade(name=f"Z {uniq.trade_name()}"), make_trade(name=f"A {uniq.trade_name()}")
        login = uniq.username()
        res = admin.post(f"{BASE}/people", json={
            "name": " Ravi ", "employment": "direct", "trade_ids": [late["id"], early["id"]],
            "username": f" {login.upper()} ", "sites": []})
        assert res.status_code == 201
        person = res.get_json()
        assert person["name"] == "Ravi" and person["employment"] == "direct" and person["active"] == 1
        assert person["username"] == login and person["has_login"] is True
        assert [t["id"] for t in person["trades"]] == [early["id"], late["id"]]
        assert person["created_by"] == "test_it_admin"

    @pytest.mark.parametrize("trades_body", [{}, {"trade_ids": []}])
    def test_person_with_no_trades(self, engineer, trades_body):
        res = engineer.post(f"{BASE}/people", json={"name": "Operator A", "employment": "direct", **trades_body})
        assert res.status_code == 201
        assert res.get_json()["trades"] == [] and res.get_json()["has_login"] is False

    def test_list_has_trades_and_hides_inactive(self, admin, make_trade, make_person):
        person = make_person(trades=[make_trade()])
        item = next(i for i in admin.get(f"{BASE}/people").get_json()["items"] if i["id"] == person["id"])
        assert item["trades"] == person["trades"]
        admin.put(f"{BASE}/people/{person['id']}", json={"active": 0})
        assert person["id"] not in _ids(admin.get(f"{BASE}/people").get_json()["items"])
        assert person["id"] in _ids(admin.get(f"{BASE}/people?include_inactive=1").get_json()["items"])

    def test_put_active_only_keeps_trades_and_login(self, admin, uniq, make_trade, make_person):
        trades, login = [make_trade(), make_trade()], uniq.username()
        person = make_person(trades=trades, username=login)
        res = admin.put(f"{BASE}/people/{person['id']}", json={"active": 0})
        assert res.status_code == 200
        body = res.get_json()
        assert body["active"] == 0 and body["username"] == login
        assert _ids(body["trades"]) == _ids(trades)

    def test_replacing_trades_keeps_granted_by_and_stamps_updated_by(self, engineer, db_rows, make_trade,
                                                                     make_person):
        kept, dropped, added = make_trade(), make_trade(), make_trade()
        person = make_person(trades=[kept, dropped])
        res = engineer.put(f"{BASE}/people/{person['id']}", json={"trade_ids": [kept["id"], added["id"]]})
        assert res.status_code == 200
        body = res.get_json()
        assert _ids(body["trades"]) == {kept["id"], added["id"]}
        assert body["updated_by"] == "test_maint_engineer" and body["updated_at"]
        granted = {r["trade_id"]: r["granted_by"] for r in db_rows(
            "SELECT trade_id, granted_by FROM person_trades WHERE person_id = %s", (person["id"],))}
        assert granted == {kept["id"]: "test_it_admin", added["id"]: "test_maint_engineer"}

    def test_unchanged_trades_do_not_stamp(self, engineer, make_trade, make_person):
        person = make_person(trades=[make_trade()])
        res = engineer.put(f"{BASE}/people/{person['id']}", json={"trade_ids": [t["id"] for t in person["trades"]]})
        assert res.status_code == 200 and res.get_json()["updated_by"] is None

    def test_all_trades_removed(self, engineer, make_trade, make_person):
        person = make_person(trades=[make_trade()])
        res = engineer.put(f"{BASE}/people/{person['id']}", json={"trade_ids": []})
        assert res.status_code == 200
        assert res.get_json()["trades"] == [] and res.get_json()["updated_by"] == "test_maint_engineer"

    def test_unknown_trade_is_400_and_nothing_is_created(self, admin, db_rows, uniq):
        name = f"Ghost {uniq.username()}"
        res = admin.post(f"{BASE}/people", json={"name": name, "employment": "direct", "trade_ids": [99999999]})
        assert res.status_code == 400 and res.get_json()["field"] == "trade_ids"
        assert db_rows("SELECT id FROM people WHERE name = %s", (name,)) == ()

    def test_inactive_trade_not_newly_given_but_kept(self, admin, make_trade, make_person):
        held, other = make_trade(), make_trade()
        person = make_person(trades=[held])
        admin.put(f"{BASE}/trades/{held['id']}", json={"active": 0})
        admin.put(f"{BASE}/trades/{other['id']}", json={"active": 0})

        refused = admin.put(f"{BASE}/people/{person['id']}", json={"trade_ids": [held["id"], other["id"]]})
        assert refused.status_code == 400 and refused.get_json()["field"] == "trade_ids"

        kept = admin.put(f"{BASE}/people/{person['id']}", json={"trade_ids": [held["id"]], "name": "Renamed"})
        assert kept.status_code == 200
        assert kept.get_json()["trades"] == [{"id": held["id"], "name": held["name"], "active": False}]
        assert admin.post(f"{BASE}/people", json={
            "name": "x", "employment": "direct", "trade_ids": [other["id"]]}).status_code == 400

    def test_duplicate_login_is_409_and_cleared_login_is_reusable(self, admin, db_rows, uniq, make_person):
        login = uniq.username()
        first = make_person(username=login)
        res = admin.post(f"{BASE}/people", json={"name": "x", "employment": "direct", "username": login.upper(),
                                                 "sites": []})
        assert res.status_code == 409 and res.get_json()["field"] == "username"
        assert res.get_json()["error"] == "Another person already has this login (it may be an inactive one)"

        second = make_person()
        res = admin.put(f"{BASE}/people/{second['id']}", json={"username": login, "sites": []})
        assert res.status_code == 409 and res.get_json()["field"] == "username"

        cleared = admin.put(f"{BASE}/people/{first['id']}", json={"username": "", "sites": []})
        assert cleared.status_code == 200 and cleared.get_json()["username"] is None
        assert db_rows("SELECT username FROM people WHERE id = %s", (first["id"],))[0]["username"] is None
        assert make_person(username=login)["username"] == login

    def test_login_is_validated(self, admin):
        res = admin.post(f"{BASE}/people", json={"name": "x", "employment": "direct", "username": "not valid"})
        assert res.status_code == 400 and res.get_json()["field"] == "username"

    def test_same_name_twice_and_employment_change(self, admin, make_person):
        a, b = make_person(name="Same Name"), make_person(name="Same Name")
        assert a["id"] != b["id"]
        res = admin.put(f"{BASE}/people/{a['id']}", json={"employment": "contractor"})
        assert res.status_code == 200 and res.get_json()["employment"] == "contractor"
        res = admin.put(f"{BASE}/people/{a['id']}", json={"employment": "contract"})
        assert res.status_code == 400 and res.get_json()["field"] == "employment"

    def test_unknown_person_is_404(self, admin):
        assert admin.put(f"{BASE}/people/99999999", json={"active": 0}).status_code == 404

    def test_a_trade_deactivated_after_creation_is_listed_inactive(self, admin, make_trade, make_person):
        trade = make_trade()
        person = make_person(trades=[trade])
        admin.put(f"{BASE}/trades/{trade['id']}", json={"active": 0})
        item = next(i for i in admin.get(f"{BASE}/people").get_json()["items"] if i["id"] == person["id"])
        assert item["trades"][0]["active"] is False


class TestLoginIsItAdmins:
    """A1 rules 2 and 3: set, changed or cleared only with masters:edit; never one's own."""

    @pytest.mark.parametrize("role", EDITORS)
    def test_editor_cannot_create_with_a_login(self, role_client, db_rows, uniq, role):
        name = f"Login {uniq.username()}"
        res = role_client(role).post(f"{BASE}/people", json={
            "name": name, "employment": "direct", "username": uniq.username()})
        assert res.status_code == 403 and res.get_json()["field"] == "username"
        assert res.get_json()["error"] == "Only IT admin can set the login"
        assert db_rows("SELECT id FROM people WHERE name = %s", (name,)) == ()

    @pytest.mark.parametrize("role", EDITORS)
    @pytest.mark.parametrize("has_login", [False, True])
    @pytest.mark.parametrize("value", ["new", None, ""])
    def test_editor_cannot_set_change_or_clear(self, role_client, db_rows, uniq, make_person, role, has_login,
                                               value):
        login = uniq.username() if has_login else None
        person = make_person(username=login) if has_login else make_person()
        body = {"username": uniq.username() if value == "new" else value}
        res = role_client(role).put(f"{BASE}/people/{person['id']}", json=body)
        assert res.status_code == 403 and res.get_json()["field"] == "username"
        assert db_rows("SELECT username FROM people WHERE id = %s", (person["id"],))[0]["username"] == login

    def test_it_admin_sets_and_changes(self, admin, uniq, make_person):
        person = make_person()
        first, second = uniq.username(), uniq.username()
        for login in (first, second):
            res = admin.put(f"{BASE}/people/{person['id']}", json={"username": login, "sites": []})
            assert res.get_json()["username"] == login

    def test_editor_update_without_login_keeps_it(self, engineer, db_rows, uniq, make_trade, make_person):
        login = uniq.username()
        person = make_person(username=login)
        res = engineer.put(f"{BASE}/people/{person['id']}", json={
            "name": "Renamed", "employment": "contractor", "trade_ids": [make_trade()["id"]]})
        assert res.status_code == 200
        body = res.get_json()
        assert body["name"] == "Renamed" and len(body["trades"]) == 1 and body["has_login"] is True
        assert db_rows("SELECT username FROM people WHERE id = %s", (person["id"],))[0]["username"] == login

    @pytest.mark.parametrize("own", ["test_it_admin", " TEST_IT_ADMIN "])
    def test_nobody_sets_their_own_login(self, admin, db_rows, make_person, own):
        res = admin.post(f"{BASE}/people", json={"name": "Me", "employment": "direct", "username": own})
        assert res.status_code == 403 and res.get_json()["field"] == "username"
        assert res.get_json()["error"] == "You can't give yourself a login"
        person = make_person()
        res = admin.put(f"{BASE}/people/{person['id']}", json={"username": own})
        assert res.status_code == 403 and res.get_json()["field"] == "username"
        assert db_rows("SELECT username FROM people WHERE id = %s", (person["id"],))[0]["username"] is None

    def test_own_login_refused_for_another_it_admin_too(self, role_client, make_person):
        res = role_client("it_admin", "kla@office.smtw.in").put(
            f"{BASE}/people/{make_person()['id']}", json={"username": "KLA@office.smtw.in"})
        assert res.status_code == 403 and res.get_json()["field"] == "username"


class TestActiveWithALogin:
    """A1 rule 1: (de)activating a person who has a login is IT admin's, checked on the locked row."""

    @pytest.mark.parametrize("role", EDITORS)
    def test_editor_cannot_deactivate_or_reactivate(self, admin, role_client, db_rows, uniq, make_person, role):
        person = make_person(username=uniq.username())
        res = role_client(role).put(f"{BASE}/people/{person['id']}", json={"active": 0})
        assert res.status_code == 403 and res.get_json()["field"] == "active"
        assert db_rows("SELECT active FROM people WHERE id = %s", (person["id"],))[0]["active"] == 1

        admin.put(f"{BASE}/people/{person['id']}", json={"active": 0})
        res = role_client(role).put(f"{BASE}/people/{person['id']}", json={"active": 1})
        assert res.status_code == 403 and res.get_json()["field"] == "active"
        assert db_rows("SELECT active FROM people WHERE id = %s", (person["id"],))[0]["active"] == 0

    def test_refused_change_writes_nothing_else(self, engineer, db_rows, uniq, make_person):
        person = make_person(username=uniq.username())
        res = engineer.put(f"{BASE}/people/{person['id']}", json={"active": 0, "name": "Changed"})
        assert res.status_code == 403
        assert db_rows("SELECT name FROM people WHERE id = %s", (person["id"],))[0]["name"] == "Test person"

    def test_it_admin_can(self, admin, uniq, make_person):
        person = make_person(username=uniq.username())
        assert admin.put(f"{BASE}/people/{person['id']}", json={"active": 0}).status_code == 200
        assert admin.put(f"{BASE}/people/{person['id']}", json={"active": 1}).status_code == 200

    @pytest.mark.parametrize("role", EDITORS)
    def test_editor_can_without_a_login(self, role_client, make_person, role):
        person = make_person()
        assert role_client(role).put(f"{BASE}/people/{person['id']}", json={"active": 0}).status_code == 200
        assert role_client(role).put(f"{BASE}/people/{person['id']}", json={"active": 1}).status_code == 200


class TestLoginMasking:
    """A1 rule 7: editors learn whether there is a login; only IT admin sees which."""

    @pytest.mark.parametrize("role, sees_has_login, sees_username", [
        ("maint_operator", False, False), ("maint_technician", False, False), ("maint_storekeeper", False, False),
        ("maint_engineer", True, False), ("maint_manager", True, False), ("it_admin", True, True),
    ])
    def test_list_rows(self, role_client, make_person, uniq, role, sees_has_login, sees_username):
        login = uniq.username()
        person = make_person(username=login)
        row = _row(role_client(role), person["id"])
        assert ("username" in row) is sees_username
        assert ("has_login" in row) is sees_has_login
        if sees_has_login:
            assert row["has_login"] is True
        if sees_username:
            assert row["username"] == login

    def test_write_responses_are_masked_too(self, engineer, uniq, make_person):
        person = make_person(username=uniq.username())
        body = engineer.put(f"{BASE}/people/{person['id']}", json={"name": "Renamed"}).get_json()
        assert "username" not in body and body["has_login"] is True


class TestAccess:

    @pytest.mark.parametrize("role", ["maint_operator", "maint_technician", "maint_storekeeper"])
    def test_others_read_but_cannot_write(self, role_client, make_trade, make_person, role):
        client, trade, person = role_client(role), make_trade(), make_person()
        assert client.get(f"{BASE}/trades").status_code == 200
        assert client.get(f"{BASE}/people").status_code == 200
        body = {"name": "x", "employment": "direct", "trade_ids": [trade["id"]]}
        assert client.post(f"{BASE}/trades", json={"name": "x"}).status_code == 403
        assert client.put(f"{BASE}/trades/{trade['id']}", json={"name": "y"}).status_code == 403
        assert client.post(f"{BASE}/people", json=body).status_code == 403
        assert client.put(f"{BASE}/people/{person['id']}", json={"active": 0}).status_code == 403

    @pytest.mark.parametrize("role", ["maint_engineer", "maint_manager", "it_admin"])
    def test_maintenance_side_and_it_admin_write(self, role_client, uniq, role):
        client = role_client(role)
        trade = client.post(f"{BASE}/trades", json={"name": uniq.trade_name()})
        assert trade.status_code == 201
        person = client.post(f"{BASE}/people", json={
            "name": "x", "employment": "contractor", "trade_ids": [trade.get_json()["id"]]})
        assert person.status_code == 201
        assert person.get_json()["created_by"] == f"test_{role}"
        assert client.put(f"{BASE}/people/{person.get_json()['id']}", json={"active": 0}).status_code == 200
        assert client.put(f"{BASE}/trades/{trade.get_json()['id']}", json={"active": 0}).status_code == 200
