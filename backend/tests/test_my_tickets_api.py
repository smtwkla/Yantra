"""The Me page's two reads (S031 § 5, § 6, § 8): ``GET /api/tickets?raised=me`` and
``GET /api/tickets/activity``, against the test DB.  Needs the dev MariaDB container
(tooling/dev/dev-db-up.bat).

Each test makes its own people and tickets and asserts only on them: the session database is
shared by every test.
"""

import pytest

import access_control
import db_helpers
from tests.conftest import MASTERS, TICKETS

ACTIVITY = f"{TICKETS}/activity"


@pytest.fixture
def db_down(monkeypatch):
    """Every get_db() in the request raises DBUnavailable (as tests/test_auth.py's fixture)."""
    monkeypatch.setattr(db_helpers, "ensure_schema", lambda _config: "Can't connect (test)")
    monkeypatch.setattr(access_control, "ensure_schema", lambda _config: "Can't connect (test)")


@pytest.fixture
def site(unit):
    return {"id": unit["site_id"]}


@pytest.fixture
def at_site(user_at_sites, site, unit):
    """at_site(role) -> (client, person): a user with a Team record holding ``role`` at the
    ticket's site, on its unit."""
    return lambda role: user_at_sites([(site, role, [unit])])


@pytest.fixture
def tech(at_site):
    return at_site("maint_technician")


@pytest.fixture
def eng(at_site):
    return at_site("maint_engineer")


def ids(res):
    assert res.status_code == 200, res.get_json()
    return [item["id"] for item in res.get_json()["items"]]


def raised(client, **query):
    return client.get(TICKETS, query_string={"raised": "me", **query})


def acknowledge(client, ticket):
    res = client.post(f"{TICKETS}/{ticket['id']}/moves/acknowledge", json={})
    assert res.status_code == 200, res.get_json()


def lose_unit(admin, person, site, other_unit):
    """The person keeps the site but holds another unit only."""
    res = admin.put(f"{MASTERS}/people/{person['id']}/sites/{site['id']}",
                    json={"role": "maint_technician", "all_units": False, "unit_ids": [other_unit["id"]]})
    assert res.status_code == 200, res.get_json()


class TestRaisedByMe:

    def test_my_raise_and_the_one_naming_me_are_listed(self, tech, eng, make_ticket, machine):
        client, person = tech
        eng_client, _ = eng
        mine = make_ticket(machine, client=client)
        named = make_ticket(machine, client=eng_client, reported_by_id=person["id"])
        other = make_ticket(machine, client=eng_client)
        listed = ids(raised(client, state="all"))
        assert mine["id"] in listed and named["id"] in listed
        assert other["id"] not in listed

    def test_a_user_with_no_team_record_gets_the_raises_of_their_login(self, role_client, uniq, make_ticket, machine,
                                                                       eng):
        client = role_client("it_admin", uniq.username())
        mine = make_ticket(machine, client=client)
        other = make_ticket(machine, client=eng[0])
        listed = ids(raised(client, state="all"))
        assert mine["id"] in listed and other["id"] not in listed

    def test_state_and_the_other_filters_combine_by_and(self, tech, make_ticket, machine, set_ticket_state):
        client, _ = tech
        open_one = make_ticket(machine, client=client)
        closed_one = make_ticket(machine, client=client)
        set_ticket_state(closed_one, "closed")
        assert ids(raised(client, state="closed")) == [closed_one["id"]]
        assert ids(raised(client, state="open")) == [open_one["id"]]
        assert ids(raised(client, state="all", q=open_one["serial"])) == [open_one["id"]]

    def test_a_ticket_at_a_unit_i_lost_is_not_listed(self, admin, tech, make_ticket, machine, site, make_unit):
        client, person = tech
        mine = make_ticket(machine, client=client)
        assert mine["id"] in ids(raised(client, state="all"))
        lose_unit(admin, person, site, make_unit(site))
        assert mine["id"] not in ids(raised(client, state="all"))

    def test_another_value_is_400(self, tech):
        res = raised(tech[0], raised="you")
        assert res.status_code == 400 and res.get_json()["field"] == "raised"
        assert res.get_json()["error"] == "raised must be one of: me"

    def test_a_storekeeper_is_403(self, role_client):
        assert raised(role_client("maint_storekeeper")).status_code == 403


class TestActivity:

    def test_what_i_recorded_newest_first(self, tech, eng, db_rows, make_ticket, machine):
        client, person = tech
        eng_client, _ = eng
        ticket = make_ticket(machine, client=client)
        acknowledge(client, ticket)
        eng_client.post(f"{TICKETS}/{ticket['id']}/notes", json={"remark": "Line of the engineer"})

        res = client.get(ACTIVITY)
        assert res.status_code == 200, res.get_json()
        items = res.get_json()["items"]
        assert [i["event"] for i in items] == ["assigned", "acknowledged", "raised"]
        # The same second for all lines: the higher id comes first (the assigned line is written after the move line)
        db_rows("UPDATE ticket_events SET created_at = '2026-10-23 10:00:00' WHERE ticket_id = %s", (ticket["id"],))
        again = client.get(ACTIVITY).get_json()["items"]
        assert [i["id"] for i in again] == sorted((i["id"] for i in again), reverse=True)
        assert [i["event"] for i in again] == ["assigned", "acknowledged", "raised"]
        first = items[1]
        assert first["ticket"] == {"id": ticket["id"], "serial": ticket["serial"], "intensity": "critical",
                                   "state": "acknowledged",
                                   "machine": {"id": machine["id"], "code": machine["code"], "name": machine["name"]}}
        assert first["person"] is None and first["created_at"] and first["occurred_at"]
        assert items[0]["person"] == {"id": person["id"], "name": person["name"]}
        assert items[2]["intensity"] == "critical"

    def test_a_note_shows_its_current_text_after_a_correction(self, tech, eng, make_ticket, machine):
        client, _ = tech
        eng_client, _ = eng
        ticket = make_ticket(machine, client=client)
        note = client.post(f"{TICKETS}/{ticket['id']}/notes", json={"remark": "Belt lose"}).get_json()["events"][-1]
        res = eng_client.put(f"{TICKETS}/{ticket['id']}/notes/{note['id']}", json={"remark": "Belt loose"})
        assert res.status_code == 200, res.get_json()
        items = client.get(ACTIVITY).get_json()["items"]
        assert [i["remark"] for i in items if i["event"] == "note"] == ["Belt loose"]

    def test_total_and_paging(self, tech, make_ticket, machine):
        client, _ = tech
        ticket = make_ticket(machine, client=client)
        acknowledge(client, ticket)
        everything = client.get(ACTIVITY).get_json()
        assert everything["total"] == 3 and everything["page"] == 1 and everything["per_page"] == 50
        second = client.get(ACTIVITY, query_string={"per_page": 1, "page": 2}).get_json()
        assert second["total"] == 3 and second["page"] == 2 and second["per_page"] == 1
        assert [i["id"] for i in second["items"]] == [everything["items"][1]["id"]]

    def test_a_ticket_at_a_unit_i_lost_drops_out(self, admin, tech, make_ticket, machine, site, make_unit):
        client, person = tech
        make_ticket(machine, client=client)
        assert client.get(ACTIVITY).get_json()["total"] == 1
        lose_unit(admin, person, site, make_unit(site))
        assert client.get(ACTIVITY).get_json() == {"items": [], "total": 0, "page": 1, "per_page": 50}

    def test_it_admin_without_a_team_record_sees_their_own_lines(self, role_client, uniq, make_ticket, machine):
        client = role_client("it_admin", uniq.username())
        ticket = make_ticket(machine, client=client)
        assert [(i["event"], i["ticket"]["id"]) for i in client.get(ACTIVITY).get_json()["items"]] == [
            ("raised", ticket["id"])]

    def test_a_login_in_another_case_still_matches(self, tech, db_rows, make_ticket, machine):
        client, person = tech
        ticket = make_ticket(machine, client=client)
        db_rows("UPDATE ticket_events SET created_by = %s WHERE ticket_id = %s",
                (person["username"].upper(), ticket["id"]))
        assert client.get(ACTIVITY).get_json()["total"] == 1

    def test_a_storekeeper_is_403(self, role_client):
        assert role_client("maint_storekeeper").get(ACTIVITY).status_code == 403

    @pytest.mark.parametrize("query", [{"page": 0}, {"per_page": 0}, {"per_page": 201}])
    def test_a_bad_page_is_400(self, tech, query):
        assert tech[0].get(ACTIVITY, query_string=query).status_code == 400

    def test_the_database_down_is_503(self, tech, db_down):
        assert tech[0].get(ACTIVITY).status_code == 503
