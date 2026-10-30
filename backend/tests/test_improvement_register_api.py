"""The improvement register (S076 § 8.2), against the test DB.  Needs the dev MariaDB container.

Each test makes its own site, units and machines (the ``world`` fixture), so counts are exact in
the kept worker database.  Improvements come from S067's start route; the states, times, closes and
countermeasure rows that a route would need weeks of watch for are written straight to the rows,
keeping S072's and S070's CHECKs true (chk_improvements_watch_from, chk_improvements_closed,
chk_improvements_close_remark, chk_improvement_actions_done).
"""

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

import improvements
from tests.conftest import MASTERS
from tests.test_improvements_api import IMPROVEMENTS, started
from tests.ticket_helpers import now_ist

REGISTER = f"{IMPROVEMENTS}/register"
DAY = timedelta(days=1)
OCTOBER = {"from": "2026-10-01", "to": "2026-10-31"}


def minute(dt):
    return dt.replace(second=0, microsecond=0)


@pytest.fixture
def world(make_site, make_unit, make_equipment, user_at_sites, make_ticket, set_ticket_state, db_rows):
    """A site of two units with a machine each, its engineer (the lead), and ``make`` to add improvements."""
    site = make_site()
    units = [make_unit(site), make_unit(site)]
    machines = [make_equipment(unit=unit) for unit in units]
    client, person = user_at_sites([(site, "maint_engineer", "all")])

    def make(machine=None, created_at=None, state=None, watch_from=None, closed_at=None, closed_by=None,
             remark=None, follow_up_of=None):
        machine = machine or machines[0]
        ticket = make_ticket(machine)
        set_ticket_state(ticket, "back_in_service")
        improvement = started(client, ticket, person)
        sets, params = [], []
        for column, value in (("created_at", created_at), ("state", state), ("watch_from", watch_from),
                              ("closed_at", closed_at), ("closed_by", closed_by), ("close_remark", remark),
                              ("follow_up_of_id", follow_up_of)):
            if value is not None:
                sets.append(f"{column} = %s")
                params.append(value)
        if sets:
            db_rows(f"UPDATE improvements SET {', '.join(sets)} WHERE id = %s", (*params, improvement["id"]))
        return improvement

    return SimpleNamespace(site=site, units=units, machines=machines, client=client, person=person, make=make)


@pytest.fixture
def add_action(world, db_rows):
    """add_action(improvement, due=None, state="open", owner=None, kind="corrective") -> the action id; the due
    date is written to the row (the API only takes a date from the problem's day on)."""
    def add(improvement, due=None, state="open", owner=None, kind="corrective"):
        owner = owner or world.person
        res = world.client.post(f"{IMPROVEMENTS}/{improvement['id']}/actions", json={
            "kind": kind, "text": "Fit a sealed contact block", "owner_id": owner["id"],
            "due_date": (now_ist().date() + 7 * DAY).isoformat()})
        assert res.status_code == 201, res.get_json()
        action_id = res.get_json()["actions"][-1]["id"]
        sets, params = ["due_date = %s"], [due or (now_ist().date() + 7 * DAY)]
        if state == "done":
            sets += ["state = 'done'", "done_text = 'Done'", "done_at = %s", "done_by = 'someone'"]
            params.append(now_ist())
        elif state == "cancelled":
            sets += ["state = 'cancelled'", "cancel_reason = 'No longer needed'", "cancelled_at = %s",
                     "cancelled_by = 'someone'"]
            params.append(now_ist())
        db_rows(f"UPDATE improvement_actions SET {', '.join(sets)} WHERE id = %s", (*params, action_id))
        return action_id
    return add


def register(client, **params):
    return client.get(REGISTER, query_string=params)


def ok(client, **params):
    res = register(client, **params)
    assert res.status_code == 200, res.get_json()
    return res.get_json()


def serials(section):
    return [item["serial"] for item in section["items"]]


def refusal(res, status, message=None, field=None):
    assert res.status_code == status, res.get_json()
    body = res.get_json()
    if message is not None:
        assert body["error"] == message
    if field is not None:
        assert body["field"] == field
    return body


# ---------------------------------------------------------------------------
# Started in the period
# ---------------------------------------------------------------------------

class TestStarted:

    def test_the_period_edges_oldest_first_and_a_follow_up(self, world):
        before = world.make(created_at=datetime(2026, 9, 30, 23, 59))
        first = world.make(created_at=datetime(2026, 10, 1, 0, 0))
        second = world.make(created_at=datetime(2026, 10, 31, 23, 59))
        after = world.make(created_at=datetime(2026, 11, 1, 0, 0))
        follow_up = world.make(created_at=datetime(2026, 10, 15, 8, 0), follow_up_of=before["id"])
        data = ok(world.client, **OCTOBER)
        assert serials(data["started"]) == [first["serial"], follow_up["serial"], second["serial"]]
        assert after["serial"] not in serials(data["started"]) and data["started"]["count"] == 3
        item = data["started"]["items"][1]
        assert item["follow_up_of"] == {"id": before["id"], "serial": before["serial"]}
        assert data["started"]["items"][0]["follow_up_of"] is None
        assert item["state"] == "analysing" and item["lead_name"] == world.person["name"]
        assert item["machine"]["code"] == world.machines[0]["code"] and item["started_at"].startswith("2026-10-15T08:00")

    def test_a_dropped_one_counts_too(self, world):
        world.make(created_at=datetime(2026, 10, 5, 8, 0), state="dropped", closed_at=datetime(2026, 10, 6, 8, 0),
                   closed_by="x", remark="Duplicate")
        data = ok(world.client, **OCTOBER)
        assert data["started"]["count"] == 1 and data["started"]["items"][0]["state"] == "dropped"


# ---------------------------------------------------------------------------
# Open now
# ---------------------------------------------------------------------------

class TestOpen:

    def test_states_ages_and_actions(self, world, add_action, db_rows):
        now = now_ist()
        analysing = world.make(created_at=now)
        actions_open = world.make(created_at=now - 31 * DAY)
        watching = world.make(created_at=now - 91 * DAY, state="watching", watch_from=now - 10 * DAY)
        ended = world.make(created_at=now - 181 * DAY, state="watching", watch_from=now - 100 * DAY)
        closed = world.make(created_at=now - 5 * DAY, state="closed_effective", watch_from=now - 40 * DAY,
                            closed_at=now, closed_by="x")
        dropped = world.make(created_at=now - 5 * DAY, state="dropped", closed_at=now, closed_by="x", remark="Dup")
        add_action(actions_open, due=now.date() + DAY)
        add_action(actions_open, due=now.date())            # due today: not overdue
        add_action(actions_open, due=now.date() - 2 * DAY)  # overdue
        add_action(actions_open, state="done")
        add_action(actions_open, state="cancelled", due=now.date() - 9 * DAY)
        # the state is written last: adding a countermeasure settles it from the data (no root cause: Analysing)
        db_rows("UPDATE improvements SET state = 'actions_open' WHERE id = %s", (actions_open["id"],))
        data = ok(world.client, **OCTOBER)["open"]
        assert serials(data) == [ended["serial"], watching["serial"], actions_open["serial"], analysing["serial"]]
        assert closed["serial"] not in serials(data) and dropped["serial"] not in serials(data)
        by_serial = {item["serial"]: item for item in data["items"]}
        assert [by_serial[s]["state"] for s in serials(data)] == ["ready_to_verify", "watching", "actions_open", "analysing"]
        assert [by_serial[s]["age_days"] for s in serials(data)] == [181, 91, 31, 0]
        assert (by_serial[actions_open["serial"]]["actions_open"], by_serial[actions_open["serial"]]["actions_overdue"]) == (3, 1)
        assert (by_serial[analysing["serial"]]["actions_open"], by_serial[analysing["serial"]]["actions_overdue"]) == (0, 0)
        assert data["count"] == 4
        table = {row["state"]: row for row in data["by_state"]}
        assert list(table) == ["analysing", "actions_open", "watching", "ready_to_verify"]
        assert table["ready_to_verify"]["bands"] == {"0_30": 0, "31_90": 0, "91_180": 0, "over_180": 1}
        assert table["watching"]["bands"]["91_180"] == 1 and table["actions_open"]["bands"]["31_90"] == 1
        assert table["analysing"]["total"] == 1
        assert data["band_totals"] == {"0_30": 1, "31_90": 1, "91_180": 1, "over_180": 1}

    def test_an_empty_site_keeps_every_row(self, world):
        data = ok(world.client)["open"]
        assert data["count"] == 0 and data["items"] == [] and len(data["by_state"]) == 4


# ---------------------------------------------------------------------------
# Countermeasures overdue
# ---------------------------------------------------------------------------

class TestOverdue:

    def test_only_open_and_late_on_open_improvements_most_late_first(self, world, add_action, user_at_sites, db_rows):
        today = now_ist().date()
        mine = world.make()
        owner_client, owner = user_at_sites([(world.site, "maint_technician", "all")])
        late = add_action(mine, due=today - 3 * DAY, owner=owner)
        later = add_action(mine, due=today - 10 * DAY)
        add_action(mine, due=today)                                  # due today
        add_action(mine, due=today - 5 * DAY, state="done")
        add_action(mine, due=today - 5 * DAY, state="cancelled")
        gone = world.make()
        add_action(gone, due=today - 4 * DAY)                        # an open one on a dropped improvement
        db_rows("UPDATE improvements SET state = 'dropped', closed_at = %s, closed_by = 'x', close_remark = 'Dup'"
                " WHERE id = %s", (now_ist(), gone["id"]))
        data = ok(world.client)["overdue"]
        assert [item["id"] for item in data["items"]] == [later, late] and data["count"] == 2
        assert [item["overdue_days"] for item in data["items"]] == [10, 3]
        assert data["items"][1]["owner_name"] == owner["name"] and data["items"][1]["kind"] == "corrective"
        assert data["items"][0]["improvement"] == {"id": mine["id"], "serial": mine["serial"], "title": mine["title"]}
        assert data["items"][0]["due_date"] == (today - 10 * DAY).isoformat()


# ---------------------------------------------------------------------------
# Closed in the period
# ---------------------------------------------------------------------------

class TestClosed:

    def test_results_who_closed_and_the_share(self, world, user_at_sites, db_rows):
        other_client, other = user_at_sites([(world.site, "maint_engineer", "all")])
        watch = datetime(2026, 8, 1)
        worked_by_lead = world.make(state="closed_effective", watch_from=watch, closed_at=datetime(2026, 10, 10, 9, 0),
                                    closed_by=world.person["username"], remark="Held for 90 days")
        worked_by_other = world.make(state="closed_effective", watch_from=watch, closed_at=datetime(2026, 10, 11, 9, 0),
                                     closed_by=other["username"], remark="Fine")
        failed = world.make(state="closed_not_effective", watch_from=watch, closed_at=datetime(2026, 10, 12, 9, 0),
                            closed_by="admin-login", remark="Tripped again")
        follow_up = world.make(follow_up_of=failed["id"])
        dropped_by_lead = world.make(state="dropped", closed_at=datetime(2026, 10, 13, 9, 0),
                                     closed_by=world.person["username"], remark="Duplicate of IM-1")
        old = world.make(state="closed_effective", watch_from=watch, closed_at=datetime(2026, 9, 30, 23, 59),
                         closed_by=other["username"], remark="Old")
        data = ok(world.client, **OCTOBER)["closed"]
        assert serials(data) == [worked_by_lead["serial"], worked_by_other["serial"], failed["serial"],
                                 dropped_by_lead["serial"]]
        assert old["serial"] not in serials(data)
        items = {item["serial"]: item for item in data["items"]}
        lead_row, other_row, failed_row, dropped_row = (items[s] for s in serials(data))
        assert (lead_row["state"], lead_row["by_lead"], lead_row["closed_by_name"], lead_row["remark"]) == (
            "closed_effective", True, world.person["name"], "Held for 90 days")
        assert (other_row["by_lead"], other_row["closed_by_name"]) == (False, other["name"])
        assert (failed_row["by_lead"], failed_row["closed_by_name"]) == (False, "admin-login")   # no Team record
        assert failed_row["follow_up"] == {"id": follow_up["id"], "serial": follow_up["serial"]}
        assert dropped_row["by_lead"] is None and dropped_row["remark"] == "Duplicate of IM-1"
        assert dropped_row["follow_up"] is None
        assert (data["it_worked"], data["did_not_work"], data["dropped"], data["worked_share"]) == (2, 1, 1, 67)

    def test_no_verified_close_has_no_share(self, world):
        assert ok(world.client, **OCTOBER)["closed"]["worked_share"] is None


# ---------------------------------------------------------------------------
# The period
# ---------------------------------------------------------------------------

class TestPeriod:

    @pytest.mark.parametrize("params, field", [
        ({"from": "soon"}, "from"), ({"to": "2026-02-30"}, "to"), ({"from": "2026-10-05", "to": "2026-10-04"}, "from"),
        ({"from": "2027-12-31", "to": "2028-12-31"}, "to"),
    ])
    def test_refusals(self, world, params, field):
        refusal(register(world.client, **params), 400, field=field)

    def test_a_bad_period_is_a_400_before_a_site_404(self, world):
        refusal(register(world.client, **{"from": "2026-10-05", "to": "2026-10-04"}, site_id=999999999), 400, field="from")

    def test_the_messages(self, world):
        refusal(register(world.client, **{"from": "soon"}), 400, "from must be a date, DD-MM-YYYY or YYYY-MM-DD", "from")
        refusal(register(world.client, **{"from": "2026-10-05", "to": "2026-10-04"}), 400,
                "The start must be on or before the end", "from")
        refusal(register(world.client, **{"from": "2027-12-31", "to": "2028-12-31"}), 400,
                "Choose a period of up to one year", "to")

    def test_dd_mm_yyyy_is_accepted(self, world):
        data = ok(world.client, **{"from": "30-10-2026", "to": "31-10-2026"})
        assert data["period"] == {"from": "2026-10-30", "to": "2026-10-31"}

    def test_366_days_pass(self, world):
        assert ok(world.client, **{"from": "2028-01-01", "to": "2028-12-31"})["period"]["to"] == "2028-12-31"

    def test_only_to_gives_one_month(self, world):
        assert ok(world.client, to="2026-03-15")["period"] == {"from": "2026-03-01", "to": "2026-03-15"}

    def test_only_from_gives_the_rest_of_its_month(self, world):
        assert ok(world.client, **{"from": "2026-03-15"})["period"] == {"from": "2026-03-15", "to": "2026-03-31"}

    def test_no_arguments_is_this_month_and_today_is_the_ist_date(self, world, monkeypatch):
        monkeypatch.setattr(improvements, "_now", lambda: datetime(2028, 2, 15, 9, 30))
        data = ok(world.client)
        assert data["period"] == {"from": "2028-02-01", "to": "2028-02-29"} and data["today"] == "2028-02-15"

    def test_a_bad_site_id_is_a_400(self, world):
        refusal(register(world.client, site_id="abc"), 400, field="site_id")

    def test_unknown_arguments_are_ignored(self, world):
        assert register(world.client, colour="red").status_code == 200


# ---------------------------------------------------------------------------
# Site, units and access
# ---------------------------------------------------------------------------

class TestAccess:

    def test_an_engineer_sees_their_site_only(self, world, make_site):
        other_site = make_site()
        mine = world.make()
        data = ok(world.client)
        assert [s["id"] for s in data["sites"]] == [world.site["id"]] and data["site"]["id"] == world.site["id"]
        assert data["units"] is None and mine["serial"] in serials(data["open"])
        refusal(register(world.client, site_id=other_site["id"]), 404, "Not found")
        refusal(register(world.client, site_id=999999999), 404, "Not found")

    def test_a_manager_of_two_sites_chooses(self, world, make_site, make_unit, make_equipment, make_ticket,
                                            set_ticket_state, user_at_sites, admin):
        site_b = make_site()
        machine_b = make_equipment(unit=make_unit(site_b))
        client, person = user_at_sites([(world.site, "maint_manager", "all"), (site_b, "maint_manager", "all")])
        ticket = make_ticket(machine_b)
        set_ticket_state(ticket, "back_in_service")
        in_b = started(client, ticket, person)
        in_a = world.make()
        sites = ok(client)["sites"]
        assert [s["id"] for s in sites] == [s["id"] for s in sorted(sites, key=lambda s: s["code"])]
        assert {world.site["id"], site_b["id"]} == {s["id"] for s in sites}
        first = ok(client)
        assert first["site"]["code"] == sites[0]["code"]
        shown_b = ok(client, site_id=site_b["id"])
        assert shown_b["site"]["id"] == site_b["id"] and serials(shown_b["open"]) == [in_b["serial"]]
        assert in_a["serial"] not in serials(shown_b["open"])

    def test_an_engineer_with_chosen_units_sees_those_only(self, world, user_at_sites):
        client, _ = user_at_sites([(world.site, "maint_engineer", [world.units[0]])])
        one = world.make(machine=world.machines[0])
        two = world.make(machine=world.machines[1])
        data = ok(client)
        assert serials(data["open"]) == [one["serial"]] and two["serial"] not in serials(data["open"])
        assert data["units"] == [f"{world.site['code']}.{world.units[0]['code']}"]
        assert ok(world.client)["units"] is None   # the whole site

    def test_a_machine_moved_into_the_engineers_unit_is_visible(self, world, user_at_sites, db_rows):
        client, _ = user_at_sites([(world.site, "maint_engineer", [world.units[0]])])
        moved = world.make(machine=world.machines[1])        # the improvement's unit is unit 2
        assert serials(ok(client)["open"]) == []
        db_rows("UPDATE equipment SET unit_id = %s WHERE id = %s", (world.units[0]["id"], world.machines[1]["id"]))
        assert serials(ok(client)["open"]) == [moved["serial"]]

    @pytest.mark.parametrize("role", ["maint_operator", "maint_technician", "maint_supervisor", "maint_storekeeper"])
    def test_floor_roles_get_403(self, world, user_at_sites, role):
        client, _ = user_at_sites([(world.site, role, "all")])
        refusal(register(client), 403)

    def test_it_admin_gets_403(self, admin):
        refusal(register(admin), 403)

    def test_admin_sees_every_active_site(self, world, keycloak_admin):
        data = ok(keycloak_admin, site_id=world.site["id"])
        assert data["site"]["id"] == world.site["id"] and data["units"] is None
        assert world.site["id"] in {s["id"] for s in data["sites"]}
        assert [s["code"] for s in data["sites"]] == sorted(s["code"] for s in data["sites"])

    def test_a_key_holder_with_no_active_unit_gets_an_empty_register(self, world, user_at_sites, db_rows):
        client, _ = user_at_sites([(world.site, "maint_engineer", [world.units[0]])])
        db_rows("UPDATE units SET active = 0 WHERE id = %s", (world.units[0]["id"],))
        data = ok(client)
        assert data["sites"] == [] and data["site"] is None and data["started"]["count"] == 0
        assert data["open"]["count"] == 0 and data["closed"]["worked_share"] is None

    def test_the_database_down_is_503(self, world, db_down):
        assert register(world.client).status_code == 503


def test_printed_by_is_the_readers_name(world):
    data = ok(world.client)
    assert data["printed_by"] == "Test maintenance_team"  # the login's name (the token), not a stored value
    assert data["printed_at"].endswith("+05:30") and "T" in data["printed_at"]
