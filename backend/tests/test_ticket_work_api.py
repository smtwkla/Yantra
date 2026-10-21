"""Working the ticket (S018 § 8), against the test DB.  Needs the dev MariaDB container
(tooling/dev/dev-db-up.bat).

The people who work tickets have real memberships at the ticket's site (user_at_sites), since
§ 5.8 reads the role from memberships, never from the token.  IT admin (the ``admin`` fixture)
holds every key at every site and has no Team record.
"""

import threading
import time
from datetime import timedelta

import pytest

import config
from local_db import get_local_db
from tests.conftest import EQUIPMENT, MASTERS, TICKETS
from tests.documents_helpers import JPEG, PDF, upload_to
from tests.ticket_helpers import api_time, local, now_ist, refusal
from tickets_core import ticket_times


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

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


@pytest.fixture
def ticket(make_ticket, machine):
    return make_ticket(machine)


def url(ticket, *parts):
    return "/".join([f"{TICKETS}/{ticket['id']}", *parts])


def detail(client, ticket):
    res = client.get(url(ticket))
    assert res.status_code == 200, res.get_json()
    return res.get_json()


def move(client, ticket, name, **body):
    return client.post(url(ticket, "moves", name), json=body)


def moved(client, ticket, name, **body):
    res = move(client, ticket, name, **body)
    assert res.status_code == 200, res.get_json()
    return res.get_json()


def labour(client, ticket, person, minutes=60, **body):
    return client.post(url(ticket, "labour"), json={"person_id": person["id"], "work_date": now_ist().date().isoformat(),
                                                    "minutes": minutes, **body})


def booked(client, ticket, person, **body):
    res = labour(client, ticket, person, **body)
    assert res.status_code == 201, res.get_json()
    return res.get_json()


def events(ticket_detail):
    return [e["event"] for e in ticket_detail["events"]]


def move_names(ticket_detail):
    return [m["name"] for m in ticket_detail["moves"]]


@pytest.fixture
def cause(db_rows):
    return db_rows("SELECT id FROM failure_causes WHERE code = '3.4'")[0]["id"]


@pytest.fixture
def no_cause(db_rows):
    return db_rows("SELECT id FROM failure_causes WHERE code = '5.1'")[0]["id"]


@pytest.fixture
def action(db_rows):
    return db_rows("SELECT id FROM maintenance_actions WHERE code = '1'")[0]["id"]


@pytest.fixture
def noise(db_rows):
    return db_rows("SELECT id FROM failure_modes WHERE code = 'NOI'")[0]["id"]


@pytest.fixture
def restored(admin, eng, ticket):
    """The ticket started and back in service, with one labour row by the engineer."""
    _, person = eng
    moved(admin, ticket, "start")
    moved(admin, ticket, "restore", person_id=person["id"])
    booked(admin, ticket, person)
    return ticket


# ---------------------------------------------------------------------------
# Moves
# ---------------------------------------------------------------------------

class TestMoves:

    def test_the_straight_path_by_technician_and_engineer(self, tech, eng, ticket, cause, action, noise):
        tech_client, tech_person = tech
        eng_client, eng_person = eng
        assert moved(tech_client, ticket, "acknowledge")["state"] == "acknowledged"
        assert moved(tech_client, ticket, "start")["state"] == "in_progress"
        restored = moved(tech_client, ticket, "restore", person_id=tech_person["id"])
        assert restored["state"] == "back_in_service"
        booked(eng_client, ticket, tech_person)
        closed = moved(eng_client, ticket, "close", cause_id=cause, action_id=action, failure_mode_id=noise)
        assert closed["state"] == "closed"
        assert closed["cause"]["code"] == "3.4" and closed["action"]["code"] == "1"
        assert closed["not_a_fault"] is False
        assert events(closed)[-1] == "closed"
        assert closed["moves"] == [] and closed["regrade_to"] == []
        assert closed["can_add_photos"] is False and closed["can_add_documents"] is False

    @pytest.mark.parametrize("name, state, role", [
        ("acknowledge", "raised", "maint_operator"),
        ("start", "raised", "maint_supervisor"),
        ("send-back", "back_in_service", "maint_technician"),
        ("close", "back_in_service", "maint_technician"),
        ("not-a-fault", "raised", "maint_technician"),
    ])
    def test_a_missing_key_is_403(self, at_site, ticket, set_ticket_state, name, state, role):
        set_ticket_state(ticket, state)
        client, _ = at_site(role)
        res = move(client, ticket, name, person_id=1, machine_down=True, remark="x", cause_id=1, action_id=1)
        assert res.status_code == 403

    def test_restore_by_a_storekeeper_is_403(self, role_client, ticket, eng):
        _, person = eng
        assert move(role_client("maint_storekeeper"), ticket, "restore", person_id=person["id"]).status_code == 403

    @pytest.mark.parametrize("name, state", [
        ("acknowledge", "acknowledged"), ("acknowledge", "in_progress"), ("start", "in_progress"),
        ("start", "back_in_service"), ("restore", "back_in_service"), ("send-back", "in_progress"),
        ("close", "in_progress"), ("not-a-fault", "in_progress"), ("not-a-fault", "back_in_service"),
    ])
    def test_a_wrong_state_is_409(self, admin, eng, ticket, set_ticket_state, cause, action, name, state):
        set_ticket_state(ticket, state)
        _, person = eng
        res = move(admin, ticket, name, person_id=person["id"], machine_down=True, remark="x", cause_id=cause,
                   action_id=action)
        assert refusal(res) == (409, None, "This ticket changed — reload")

    def test_unknown_move_is_404(self, admin, ticket):
        assert move(admin, ticket, "reopen").status_code == 404

    def test_a_closed_ticket_is_409_closed(self, admin, ticket, set_ticket_state):
        set_ticket_state(ticket, "closed")
        assert refusal(move(admin, ticket, "acknowledge")) == (409, None, "This ticket is closed")

    def test_moves_listed_per_user(self, at_site, tech, eng, ticket):
        operator_client, _ = at_site("maint_operator")
        assert move_names(detail(operator_client, ticket)) == ["restore"]
        assert move_names(detail(tech[0], ticket)) == ["acknowledge", "start", "restore"]
        assert move_names(detail(eng[0], ticket)) == ["acknowledge", "start", "restore", "not-a-fault"]


class TestEventTime:

    def test_a_move_without_a_time_gets_the_servers(self, admin, ticket):
        before = now_ist().replace(microsecond=0)
        acknowledged = moved(admin, ticket, "acknowledge")["events"][-1]
        assert api_time(before - timedelta(seconds=1)) <= acknowledged["occurred_at"] <= api_time(
            now_ist() + timedelta(seconds=1))

    def test_a_typed_time_before_the_last_event_is_400_naming_it(self, admin, make_ticket, machine):
        when = now_ist().replace(second=0, microsecond=0) - timedelta(hours=2)
        ticket = make_ticket(machine, occurred_at=local(when))
        moved(admin, ticket, "acknowledge", occurred_at=local(when + timedelta(minutes=30)))
        res = move(admin, ticket, "start", occurred_at=local(when + timedelta(minutes=10)))
        expected = f"Must be at or after Acknowledged, {(when + timedelta(minutes=30)):%d-%m-%Y %H:%M}"
        assert refusal(res) == (400, "occurred_at", expected)

    def test_an_assignment_does_not_hold_back_a_typed_time(self, admin, eng, make_ticket, machine):
        """Assignments and edits are stamped with the time they were recorded and take no part in
        the order rule (only the events that move the state or the intensity do)."""
        _, person = eng
        when = now_ist().replace(second=0, microsecond=0) - timedelta(hours=2)
        ticket = make_ticket(machine, occurred_at=local(when))
        assert admin.post(url(ticket, "assignees"), json={"person_id": person["id"]}).status_code == 200
        moved(admin, ticket, "restore", person_id=person["id"], occurred_at=local(when + timedelta(minutes=40)))


class TestBackInService:

    def test_without_a_person_is_400_for_everyone(self, admin, tech, at_site, ticket):
        operator_client, _ = at_site("maint_operator")
        for client in (admin, tech[0], operator_client):
            assert refusal(move(client, ticket, "restore")) == (400, "person_id", "Who did the work? Pick a name")

    def test_default_person(self, tech, at_site, role_client, admin, make_person, uniq, ticket):
        tech_client, tech_person = tech
        restore = next(m for m in detail(tech_client, ticket)["moves"] if m["name"] == "restore")
        assert restore["default_person"] == {"id": tech_person["id"], "name": tech_person["name"]}
        supervisor_client, _ = at_site("maint_supervisor")
        # The harness manager sees every unit and has no Team record
        no_person = role_client("maint_manager", uniq.username())
        username = uniq.username()
        make_person(username=username)
        it_admin_with_person = role_client("it_admin", username)
        for client in (supervisor_client, no_person, it_admin_with_person):
            restore = next(m for m in detail(client, ticket)["moves"] if m["name"] == "restore")
            assert restore["default_person"] is None

    def test_by_a_supervisor_naming_an_operator(self, at_site, make_person, give_site_role, site, ticket):
        supervisor_client, _ = at_site("maint_supervisor")
        operator_person = make_person(name="Murugan")
        give_site_role(operator_person, site)
        done = moved(supervisor_client, ticket, "restore", person_id=operator_person["id"])
        assert done["events"][-1]["person"] == {"id": operator_person["id"], "name": "Murugan"}

    def test_a_person_from_another_site_is_400(self, admin, make_person, make_site, give_site_role, ticket):
        person = make_person()
        give_site_role(person, make_site())
        assert refusal(move(admin, ticket, "restore", person_id=person["id"]))[:2] == (400, "person_id")

    def test_after_the_fact_with_a_start_across_midnight(self, admin, eng, make_ticket, machine):
        """BR4-06: started the evening before, restored after midnight."""
        _, person = eng
        restored_at = now_ist().replace(second=0, microsecond=0) - timedelta(hours=1)
        started_at = restored_at - timedelta(minutes=50)
        ticket = make_ticket(machine, occurred_at=local(started_at - timedelta(minutes=20)))
        done = moved(admin, ticket, "restore", person_id=person["id"], occurred_at=local(restored_at),
                     started_at=local(started_at))
        started, back = done["events"][-2:]
        assert (started["event"], started["occurred_at"], started["person"]["id"]) == (
            "started", api_time(started_at), person["id"])
        assert (back["event"], back["from_state"], back["occurred_at"]) == (
            "back_in_service", "in_progress", api_time(restored_at))
        assert done["times"]["repair_minutes"] == 50

    def test_started_after_the_restoration_is_400(self, admin, eng, make_ticket, machine):
        _, person = eng
        when = now_ist().replace(second=0, microsecond=0) - timedelta(hours=2)
        ticket = make_ticket(machine, occurred_at=local(when))
        res = move(admin, ticket, "restore", person_id=person["id"], occurred_at=local(when + timedelta(minutes=30)),
                   started_at=local(when + timedelta(minutes=40)))
        assert refusal(res)[:2] == (400, "started_at")

    def test_without_a_start_repair_is_unknown(self, admin, eng, ticket):
        _, person = eng
        assert moved(admin, ticket, "restore", person_id=person["id"])["times"]["repair_minutes"] is None


class TestSendBack:

    @pytest.mark.parametrize("intensity, machine_down, after, on_event", [
        ("critical", True, "critical", None),
        ("critical", False, "degraded", "degraded"),
        ("degraded", True, "critical", "critical"),
        ("initial", False, "initial", None),
    ])
    def test_intensity(self, admin, eng, make_ticket, machine, intensity, machine_down, after, on_event):
        _, person = eng
        ticket = make_ticket(machine, intensity=intensity)
        moved(admin, ticket, "restore", person_id=person["id"])
        done = moved(admin, ticket, "send-back", machine_down=machine_down, remark="Still leaking")
        assert (done["state"], done["intensity"]) == ("in_progress", after)
        sent_back = done["events"][-1]
        assert (sent_back["event"], sent_back["intensity"], sent_back["remark"]) == (
            "sent_back", on_event, "Still leaking")

    def test_needs_an_answer_and_a_remark(self, admin, restored):
        assert refusal(move(admin, restored, "send-back", remark="x"))[:2] == (400, "machine_down")
        assert refusal(move(admin, restored, "send-back", machine_down=True))[:2] == (400, "remark")


class TestClose:

    def test_without_labour_is_409(self, admin, eng, ticket, cause, action, noise):
        _, person = eng
        moved(admin, ticket, "restore", person_id=person["id"])
        res = move(admin, ticket, "close", cause_id=cause, action_id=action, failure_mode_id=noise)
        assert refusal(res) == (409, None, "Add the labour before closing")

    def test_needs_a_symptom_when_the_ticket_has_none(self, admin, restored, cause, action):
        assert refusal(move(admin, restored, "close", cause_id=cause, action_id=action))[:2] == (
            400, "failure_mode_id")

    def test_other_with_an_empty_description_is_400(self, admin, eng, make_ticket, machine, cause, action, noise,
                                                    db_rows):
        _, person = eng
        ticket = make_ticket(machine, failure_mode_id=noise, description=None)
        moved(admin, ticket, "restore", person_id=person["id"])
        booked(admin, ticket, person)
        other = db_rows("SELECT id FROM failure_modes WHERE code = 'OTH'")[0]["id"]
        res = move(admin, ticket, "close", cause_id=cause, action_id=action, failure_mode_id=other)
        assert refusal(res) == (400, "description", "Describe the problem when the symptom is Other")

    def test_a_different_symptom_overwrites_with_an_edited_line(self, admin, eng, make_ticket, machine, cause,
                                                                action, noise, db_rows):
        _, person = eng
        ticket = make_ticket(machine, failure_mode_id=noise)
        moved(admin, ticket, "restore", person_id=person["id"])
        booked(admin, ticket, person)
        vibration = db_rows("SELECT id FROM failure_modes WHERE code = 'VIB'")[0]["id"]
        done = moved(admin, ticket, "close", cause_id=cause, action_id=action, failure_mode_id=vibration)
        assert done["failure_mode"]["code"] == "VIB"
        edited, closed = done["events"][-2:]
        assert (edited["event"], edited["remark"], closed["event"]) == (
            "edited", "Symptom: Abnormal noise → Vibration", "closed")

    def test_an_inactive_cause_is_400(self, admin, engineer, restored, uniq, action, noise):
        res = engineer.post(f"{MASTERS}/failure-causes", json={"code": uniq.failure_code(), "label": uniq.failure_label(),
                                                              "cause_group": "misc", "active": False})
        assert res.status_code == 201, res.get_json()
        res = move(admin, restored, "close", cause_id=res.get_json()["id"], action_id=action, failure_mode_id=noise)
        assert refusal(res)[:2] == (400, "cause_id")

    def test_closed_is_read_only(self, admin, eng, restored, cause, action, noise):
        _, person = eng
        moved(admin, restored, "close", cause_id=cause, action_id=action, failure_mode_id=noise)
        closed = (409, None, "This ticket is closed")
        assert refusal(admin.put(url(restored), json={"description": "x"})) == closed
        assert refusal(labour(admin, restored, person)) == closed
        assert refusal(move(admin, restored, "send-back", machine_down=True, remark="x")) == closed
        assert refusal(admin.post(url(restored, "regrade"), json={"intensity": "degraded", "remark": "x"})) == closed
        assert refusal(admin.post(url(restored, "assignees"), json={"person_id": person["id"]})) == closed
        res = upload_to(admin, url(restored, "documents"), kind="photo", data=JPEG, filename="a.jpg")
        assert refusal(res) == closed

    def test_self_close_is_allowed(self, eng, ticket, cause, action, noise):
        """User decision 4: the engineer may close a ticket he worked himself."""
        client, person = eng
        moved(client, ticket, "start")
        moved(client, ticket, "restore", person_id=person["id"])
        booked(client, ticket, person)
        assert moved(client, ticket, "close", cause_id=cause, action_id=action, failure_mode_id=noise)["state"] == "closed"


class TestNotAFault:

    def test_from_raised_keeps_the_labour(self, admin, eng, ticket, no_cause):
        _, person = eng
        booked(admin, ticket, person)
        done = moved(admin, ticket, "not-a-fault", cause_id=no_cause, remark="Ran fine when I got there")
        assert (done["state"], done["not_a_fault"], done["cause"]["code"], done["action"]) == (
            "closed", True, "5.1", None)
        assert len(done["labour"]) == 1
        assert done["events"][-1]["event"] == "closed_not_a_fault"
        assert done["times"] == {"response_minutes": None, "repair_minutes": None, "downtime_minutes": None}
        assert done["can_raise_repeat"] is False

    def test_from_in_progress_is_409(self, admin, ticket, no_cause):
        moved(admin, ticket, "start")
        assert refusal(move(admin, ticket, "not-a-fault", cause_id=no_cause, remark="x"))[0] == 409

    def test_needs_a_remark(self, admin, ticket, no_cause):
        assert refusal(move(admin, ticket, "not-a-fault", cause_id=no_cause))[:2] == (400, "remark")


# ---------------------------------------------------------------------------
# Re-grade
# ---------------------------------------------------------------------------

class TestRegrade:

    def regrade(self, client, ticket, **body):
        return client.post(url(ticket, "regrade"), json=body)

    def test_up_by_an_operator_down_by_a_technician(self, at_site, tech, make_ticket, machine):
        operator_client, _ = at_site("maint_operator")
        ticket = make_ticket(machine, intensity="degraded")
        assert detail(operator_client, ticket)["regrade_to"] == ["critical"]
        res = self.regrade(operator_client, ticket, intensity="critical")
        assert res.status_code == 200, res.get_json()
        assert res.get_json()["intensity"] == "critical"
        assert res.get_json()["events"][-1]["intensity"] == "critical"
        assert detail(operator_client, ticket)["regrade_to"] == []
        assert self.regrade(operator_client, ticket, intensity="degraded", remark="runs").status_code == 403
        assert refusal(self.regrade(tech[0], ticket, intensity="degraded")) == (400, "remark", "Say why the machine runs")
        res = self.regrade(tech[0], ticket, intensity="degraded", remark="Runs at half speed")
        assert res.status_code == 200 and res.get_json()["intensity"] == "degraded"
        assert detail(tech[0], ticket)["regrade_to"] == ["critical", "initial"]

    def test_the_same_intensity_is_400(self, admin, ticket):
        assert refusal(self.regrade(admin, ticket, intensity="critical")) == (400, "intensity", "Already a breakdown")

    def test_not_after_back_in_service(self, admin, restored):
        assert self.regrade(admin, restored, intensity="degraded", remark="x").status_code == 409
        assert detail(admin, restored)["regrade_to"] == []

    def test_downtime_starts_at_the_regrade(self, admin, make_ticket, machine):
        when = now_ist().replace(second=0, microsecond=0) - timedelta(hours=2)
        ticket = make_ticket(machine, intensity="degraded", occurred_at=local(when))
        res = self.regrade(admin, ticket, intensity="critical", occurred_at=local(when + timedelta(minutes=60)))
        assert res.status_code == 200, res.get_json()
        assert 59 <= res.get_json()["times"]["downtime_minutes"] <= 61


# ---------------------------------------------------------------------------
# Edit
# ---------------------------------------------------------------------------

class TestEdit:

    def test_component_symptom_description_and_the_line(self, tech, make_equipment, machine, ticket, noise):
        part = make_equipment(parent=machine)
        res = tech[0].put(url(ticket), json={"component_id": part["id"], "failure_mode_id": noise,
                                              "description": "Bearing noise"})
        assert res.status_code == 200, res.get_json()
        done = res.get_json()
        assert done["component"]["id"] == part["id"] and done["failure_mode"]["code"] == "NOI"
        edited = done["events"][-1]
        assert edited["event"] == "edited"
        assert edited["remark"] == (f"Component: — → {part['code']} {part['name']}\n"
                                    "Symptom: — → Abnormal noise\nDescription: Stopped → Bearing noise")

    def test_component_outside_the_machine_is_400(self, admin, make_equipment, ticket):
        other = make_equipment(parent=make_equipment())
        assert refusal(admin.put(url(ticket), json={"component_id": other["id"]}))[:2] == (400, "component_id")

    def test_mode_of_another_class_is_400(self, admin, make_mode, make_class, ticket):
        mode = make_mode(cls=make_class())
        assert refusal(admin.put(url(ticket), json={"failure_mode_id": mode["id"]}))[:2] == (400, "failure_mode_id")

    def test_clearing_the_mode_with_no_description_is_400(self, admin, make_ticket, machine, noise):
        ticket = make_ticket(machine, failure_mode_id=noise, description=None)
        assert refusal(admin.put(url(ticket), json={"failure_mode_id": None}))[:2] == (400, "description")

    def test_an_operator_cannot_edit(self, operator, ticket):
        assert operator.put(url(ticket), json={"description": "x"}).status_code == 403

    def test_a_symptom_with_the_same_label_is_still_saved(self, admin, make_mode, make_class, machine, ticket,
                                                          db_rows):
        """CR1-06: the change is decided from ids.  The ticket holds a mode of another class (the
        machine's class changed since), whose label equals a mode of the machine's class."""
        old = make_mode(cls=make_class(), label="Same label")
        current = make_mode(cls={"id": machine["class_id"]}, label="Same label")
        db_rows("UPDATE tickets SET failure_mode_id = %s WHERE id = %s", (old["id"], ticket["id"]))
        done = admin.put(url(ticket), json={"failure_mode_id": current["id"]}).get_json()
        assert done["failure_mode"]["id"] == current["id"]
        assert events(done) == ["raised"]
        assert db_rows("SELECT failure_mode_id FROM tickets WHERE id = %s", (ticket["id"],))[0][
            "failure_mode_id"] == current["id"]

    def test_no_change_writes_no_line(self, admin, ticket):
        done = admin.put(url(ticket), json={"description": "Stopped"}).get_json()
        assert events(done) == ["raised"]


# ---------------------------------------------------------------------------
# Assignment
# ---------------------------------------------------------------------------

class TestAssignment:

    def test_add_and_remove(self, eng, tech, restored):
        client, _ = eng
        _, tech_person = tech
        res = client.post(url(restored, "assignees"), json={"person_id": tech_person["id"]})
        assert res.status_code == 200, res.get_json()
        assert {a["id"] for a in res.get_json()["assignees"]} >= {tech_person["id"]}
        assert res.get_json()["events"][-1]["event"] == "assigned"
        again = client.post(url(restored, "assignees"), json={"person_id": tech_person["id"]})
        assert again.status_code == 200
        assert events(again.get_json()).count("assigned") == events(res.get_json()).count("assigned")
        removed = client.delete(url(restored, "assignees", str(tech_person["id"])))
        assert removed.status_code == 200
        assert tech_person["id"] not in [a["id"] for a in removed.get_json()["assignees"]]
        assert removed.get_json()["events"][-1]["event"] == "unassigned"
        assert client.delete(url(restored, "assignees", str(tech_person["id"]))).status_code == 404

    def test_an_operator_or_supervisor_is_400(self, admin, at_site, ticket):
        for role in ("maint_operator", "maint_supervisor"):
            _, person = at_site(role)
            assert refusal(admin.post(url(ticket, "assignees"), json={"person_id": person["id"]}))[:2] == (
                400, "person_id")

    def test_a_technician_cannot_assign(self, tech, ticket):
        assert tech[0].post(url(ticket, "assignees"), json={"person_id": tech[1]["id"]}).status_code == 403

    def test_auto_assign_on_start(self, tech, eng, make_ticket, machine):
        for client, person in (tech, eng):
            ticket = make_ticket(machine)
            done = moved(client, ticket, "start")
            assert done["assignees"] == [{"id": person["id"], "name": person["name"]}]
            assert events(done)[-2:] == ["started", "assigned"]
            assert done["events"][-1]["person"]["id"] == person["id"]

    def test_recording_as(self, tech, role_client, make_person, uniq, ticket):
        client, person = tech
        ack = next(m for m in detail(client, ticket)["moves"] if m["name"] == "acknowledge")
        assert ack["recording_as"] == {"id": person["id"], "name": person["name"]}
        username = uniq.username()
        make_person(username=username)
        for other in (role_client("maint_manager", uniq.username()), role_client("it_admin", username)):
            ack = next(m for m in detail(other, ticket)["moves"] if m["name"] == "acknowledge")
            assert ack["recording_as"] is None

    def test_it_admin_with_a_team_record_is_not_assigned(self, role_client, make_person, uniq, ticket):
        username = uniq.username()
        make_person(username=username)
        assert moved(role_client("it_admin", username), ticket, "start")["assignees"] == []

    def test_assigned_to_me(self, tech, role_client, uniq, make_ticket, machine):
        client, person = tech
        mine = make_ticket(machine)
        other = make_ticket(machine)
        moved(client, mine, "acknowledge")
        res = client.get(TICKETS, query_string={"assigned": "me"})
        assert [t["id"] for t in res.get_json()["items"]] == [mine["id"]]
        assert res.get_json()["items"][0]["assignees"] == [{"id": person["id"], "name": person["name"]}]
        listed = {t["id"]: t for t in client.get(TICKETS).get_json()["items"]}
        assert listed[other["id"]]["assignees"] == []
        nobody = role_client("maint_technician", uniq.username())
        assert nobody.get(TICKETS, query_string={"assigned": "me"}).get_json()["items"] == []

    def test_auth_me_person_id(self, tech, role_client, uniq):
        client, person = tech
        assert client.get("/api/auth/me").get_json()["person_id"] == person["id"]
        assert role_client("maint_technician", uniq.username()).get("/api/auth/me").get_json()["person_id"] is None


# ---------------------------------------------------------------------------
# Labour
# ---------------------------------------------------------------------------

class TestLabour:

    def test_add_change_remove(self, tech, ticket, make_trade, make_person, give_site_role, site):
        client, _ = tech
        trade = make_trade()
        fitter = make_person(name="Fitter", trades=[trade])
        give_site_role(fitter, site, "maint_technician")
        assert refusal(labour(client, ticket, fitter))[:2] == (400, "trade_id")
        done = booked(client, ticket, fitter, minutes=85, trade_id=trade["id"])
        row = done["labour"][0]
        assert (row["person"]["id"], row["trade"]["id"], row["minutes"]) == (fitter["id"], trade["id"], 85)
        changed = client.put(url(ticket, "labour", str(row["id"])), json={
            "person_id": fitter["id"], "trade_id": trade["id"], "work_date": row["work_date"], "minutes": 30})
        assert changed.status_code == 200 and changed.get_json()["labour"][0]["minutes"] == 30
        removed = client.delete(url(ticket, "labour", str(row["id"])))
        assert removed.status_code == 200 and removed.get_json()["labour"] == []
        assert client.delete(url(ticket, "labour", str(row["id"]))).status_code == 404

    def test_an_operator_or_supervisor_at_the_site_may_be_booked(self, admin, at_site, ticket):
        for role in ("maint_operator", "maint_supervisor"):
            _, person = at_site(role)
            booked(admin, ticket, person)

    def test_a_person_without_a_membership_is_400(self, admin, make_person, ticket):
        assert refusal(labour(admin, ticket, make_person()))[:2] == (400, "person_id")

    def test_minutes_and_date_limits(self, admin, eng, ticket):
        _, person = eng
        assert refusal(labour(admin, ticket, person, minutes=0))[:2] == (400, "minutes")
        assert refusal(labour(admin, ticket, person, minutes=1441))[:2] == (400, "minutes")
        tomorrow = (now_ist().date() + timedelta(days=1)).isoformat()
        assert refusal(labour(admin, ticket, person, work_date=tomorrow))[:2] == (400, "work_date")

    def test_an_operator_cannot_book(self, operator, eng, ticket):
        assert labour(operator, ticket, eng[1]).status_code == 403


# ---------------------------------------------------------------------------
# Repeat
# ---------------------------------------------------------------------------

class TestRepeat:

    def test_same_machine_within_seven_days(self, admin, restored, machine):
        assert detail(admin, restored)["can_raise_repeat"] is True
        res = admin.post(TICKETS, json={"equipment_id": machine["id"], "intensity": "critical",
                                        "description": "Again", "repeat_of_id": restored["id"]})
        assert res.status_code == 201, res.get_json()
        assert res.get_json()["repeat_of"] == {"id": restored["id"], "serial": restored["serial"]}
        assert [r["id"] for r in detail(admin, restored)["repeats"]] == [res.get_json()["id"]]

    def test_another_machine_is_400(self, admin, restored, make_equipment):
        res = admin.post(TICKETS, json={"equipment_id": make_equipment()["id"], "intensity": "critical",
                                        "description": "x", "repeat_of_id": restored["id"]})
        assert refusal(res) == (400, "repeat_of_id", "The earlier ticket is on another machine")

    def test_too_old_is_400(self, admin, restored, machine, db_rows):
        db_rows("UPDATE ticket_events SET occurred_at = %s WHERE ticket_id = %s",
                (now_ist() - timedelta(days=9), restored["id"]))
        assert detail(admin, restored)["can_raise_repeat"] is False
        res = admin.post(TICKETS, json={"equipment_id": machine["id"], "intensity": "critical",
                                        "description": "x", "repeat_of_id": restored["id"]})
        assert refusal(res)[:2] == (400, "repeat_of_id")

    def test_a_not_a_fault_ticket_cannot_be_repeated(self, admin, ticket, machine, no_cause):
        moved(admin, ticket, "not-a-fault", cause_id=no_cause, remark="x")
        res = admin.post(TICKETS, json={"equipment_id": machine["id"], "intensity": "critical",
                                        "description": "x", "repeat_of_id": ticket["id"]})
        assert refusal(res)[:2] == (400, "repeat_of_id")

    def test_a_ticket_sent_back_cannot_be_repeated(self, admin, restored, machine):
        """CR1-02: its restoration is inside the window, but it is being worked again."""
        moved(admin, restored, "send-back", machine_down=True, remark="Still leaking")
        assert detail(admin, restored)["can_raise_repeat"] is False
        res = admin.post(TICKETS, json={"equipment_id": machine["id"], "intensity": "critical",
                                        "description": "x", "repeat_of_id": restored["id"]})
        assert refusal(res) == (400, "repeat_of_id", "That ticket can't be repeated: it is not back in service")

    def test_never_restored_is_400(self, admin, ticket, machine):
        res = admin.post(TICKETS, json={"equipment_id": machine["id"], "intensity": "critical",
                                        "description": "x", "repeat_of_id": ticket["id"]})
        assert refusal(res)[:2] == (400, "repeat_of_id")


# ---------------------------------------------------------------------------
# Detail, pickers, documents, access
# ---------------------------------------------------------------------------

class TestDetail:

    def test_times_match_the_core(self, admin, eng, make_ticket, machine, db_rows):
        _, person = eng
        start = now_ist().replace(second=0, microsecond=0) - timedelta(hours=1)
        ticket = make_ticket(machine, occurred_at=local(start))
        moved(admin, ticket, "acknowledge", occurred_at=local(start + timedelta(minutes=5)))
        moved(admin, ticket, "start", occurred_at=local(start + timedelta(minutes=10)))
        done = moved(admin, ticket, "restore", person_id=person["id"], occurred_at=local(start + timedelta(minutes=40)))
        assert done["times"] == {"response_minutes": 5, "repair_minutes": 30, "downtime_minutes": 40}
        rows = db_rows("SELECT event, occurred_at, intensity FROM ticket_events WHERE ticket_id = %s"
                       " ORDER BY occurred_at, id", (ticket["id"],))
        assert ticket_times(rows, now_ist()) == done["times"]

    def test_permissions_are_the_keys_at_the_tickets_site(self, user_at_sites, make_site, site, unit, ticket):
        client, _ = user_at_sites([(site, "maint_operator", [unit]), (make_site(), "maint_engineer", "all")])
        shown = detail(client, ticket)
        assert "ticket:assign" not in shown["permissions"] and "ticket:restore" in shown["permissions"]
        assert shown["regrade_to"] == []

    def test_can_add_documents(self, tech, operator, admin, ticket, set_ticket_state):
        assert detail(tech[0], ticket)["can_add_documents"] is True
        assert detail(operator, ticket)["can_add_documents"] is False
        set_ticket_state(ticket, "closed")
        assert detail(admin, ticket)["can_add_documents"] is False

    def test_a_document_upload_by_a_technician(self, tech, ticket):
        res = upload_to(tech[0], url(ticket, "documents"), data=PDF)
        assert res.status_code == 201, res.get_json()


class TestPickersByTicket:

    def test_people_and_modes_after_a_cross_site_move(self, admin, make_unit, make_person, give_site_role, site,
                                                      make_mode, machine, ticket):
        here = make_person(name="Aa here")
        give_site_role(here, site, "maint_technician")
        new_unit = make_unit()
        there = make_person(name="Aa there")
        give_site_role(there, {"id": new_unit["site_id"]})
        mode = make_mode(cls={"id": machine["class_id"]})
        assert admin.put(f"{EQUIPMENT}/{machine['id']}", json={"unit_id": new_unit["id"]}).status_code == 200
        people = admin.get(f"{TICKETS}/people", query_string={"ticket_id": ticket["id"]}).get_json()["items"]
        ids = [p["id"] for p in people]
        assert here["id"] in ids and there["id"] not in ids
        assert next(p for p in people if p["id"] == here["id"])["assignable"] is True
        modes = admin.get(f"{TICKETS}/modes", query_string={"ticket_id": ticket["id"]}).get_json()["items"]
        assert modes[0]["id"] == mode["id"]

    def test_outside_access_is_404_and_no_anchor_is_400(self, user_with_units, make_unit, admin, ticket):
        other = user_with_units("maint_operator", [make_unit()])
        assert other.get(f"{TICKETS}/people", query_string={"ticket_id": ticket["id"]}).status_code == 404
        assert other.get(f"{TICKETS}/modes", query_string={"ticket_id": ticket["id"]}).status_code == 404
        assert refusal(admin.get(f"{TICKETS}/people"))[:2] == (400, "equipment_id")


class TestAccess:

    def test_every_route_is_404_outside_the_users_units(self, user_with_units, make_unit, eng, ticket):
        other = user_with_units("maint_engineer", [make_unit()])
        person = eng[1]
        for res in (move(other, ticket, "acknowledge"),
                    other.post(url(ticket, "regrade"), json={"intensity": "degraded", "remark": "x"}),
                    other.put(url(ticket), json={"description": "x"}),
                    other.post(url(ticket, "assignees"), json={"person_id": person["id"]}),
                    labour(other, ticket, person)):
            assert res.status_code == 404, res.get_json()

    def test_keys_are_checked_at_the_tickets_site(self, admin, user_at_sites, make_unit, make_site, machine, ticket):
        """A technician at the machine's new site reads the ticket but may not work it."""
        new_site = make_site()
        new_unit = make_unit(new_site)
        assert admin.put(f"{EQUIPMENT}/{machine['id']}", json={"unit_id": new_unit["id"]}).status_code == 200
        client, _ = user_at_sites([(new_site, "maint_technician", [new_unit])])
        assert client.get(url(ticket)).status_code == 200
        assert move_names(detail(client, ticket)) == []
        assert move(client, ticket, "acknowledge").status_code == 403


class TestConcurrency:

    def test_a_stale_state_is_409(self, admin, ticket):
        moved(admin, ticket, "start")
        assert refusal(move(admin, ticket, "acknowledge")) == (409, None, "This ticket changed — reload")

    def test_a_move_waits_for_the_ticket_lock_and_sees_the_new_state(self, admin, ticket):
        """BR1-13: one connection holds the ticket row; a move through the API blocks on it, and
        after the first commits a start, it answers 409."""
        conn = get_local_db(config.DB_CONFIG)
        result = {}
        try:
            with conn.cursor() as cur:
                cur.execute("START TRANSACTION")
                cur.execute("SELECT id FROM tickets WHERE id = %s FOR UPDATE", (ticket["id"],))
                worker = threading.Thread(target=lambda: result.update(res=move(admin, ticket, "acknowledge")))
                worker.start()
                time.sleep(1)
                assert worker.is_alive(), "the move did not wait for the lock"
                cur.execute("UPDATE tickets SET state = 'in_progress' WHERE id = %s", (ticket["id"],))
                cur.execute("COMMIT")
            worker.join(timeout=30)
        finally:
            conn.close()
        assert refusal(result["res"]) == (409, None, "This ticket changed — reload")


# ---------------------------------------------------------------------------
# Already fixed: raise and mark back in service in one go (A1)
# ---------------------------------------------------------------------------

class TestAlreadyFixed:

    @staticmethod
    def raise_fixed(client, machine, restore, **body):
        return client.post(TICKETS, json={"equipment_id": machine["id"], "intensity": "critical",
                                          "description": "Carbon brushes", "restore": restore, **body})

    @pytest.fixture
    def nothing_written(self, db_rows, machine):
        """Asserts a refused raise left no ticket, no event and no serial number behind."""
        def state():
            tickets = db_rows("SELECT COUNT(*) AS n FROM tickets WHERE equipment_id = %s", (machine["id"],))[0]["n"]
            events_n = db_rows("SELECT COUNT(*) AS n FROM ticket_events e JOIN tickets t ON t.id = e.ticket_id"
                               " WHERE t.equipment_id = %s", (machine["id"],))[0]["n"]
            counters = db_rows("SELECT scope, last_value FROM serial_counters WHERE scope LIKE 'TK:%%'")
            return tickets, events_n, sorted((r["scope"], r["last_value"]) for r in counters)
        before = state()
        yield
        assert state() == before

    def test_without_a_start(self, admin, eng, machine):
        _, person = eng
        failed_at = now_ist().replace(second=0, microsecond=0) - timedelta(hours=2)
        restored_at = failed_at + timedelta(minutes=45)
        res = self.raise_fixed(admin, machine, {"person_id": person["id"], "occurred_at": local(restored_at)},
                               occurred_at=local(failed_at))
        assert res.status_code == 201, res.get_json()
        done = res.get_json()
        assert done["state"] == "back_in_service"
        assert events(done) == ["raised", "back_in_service"]
        back = done["events"][-1]
        assert (back["from_state"], back["occurred_at"], back["person"]["id"]) == (
            "raised", api_time(restored_at), person["id"])
        assert done["times"] == {"response_minutes": None, "repair_minutes": None, "downtime_minutes": 45}

    def test_with_a_start(self, admin, eng, machine):
        _, person = eng
        failed_at = now_ist().replace(second=0, microsecond=0) - timedelta(hours=2)
        started_at = failed_at + timedelta(minutes=15)
        restored_at = failed_at + timedelta(minutes=45)
        done = self.raise_fixed(admin, machine, {"person_id": person["id"], "occurred_at": local(restored_at),
                                                 "started_at": local(started_at)},
                                occurred_at=local(failed_at)).get_json()
        assert done["state"] == "back_in_service"
        assert events(done) == ["raised", "started", "back_in_service"]
        assert [e["person"]["id"] for e in done["events"][1:]] == [person["id"], person["id"]]
        assert done["times"] == {"response_minutes": 15, "repair_minutes": 30, "downtime_minutes": 45}

    def test_no_time_given_is_now(self, admin, eng, machine):
        before = now_ist().replace(microsecond=0)
        done = self.raise_fixed(admin, machine, {"person_id": eng[1]["id"]}).get_json()
        back = done["events"][-1]
        assert back["event"] == "back_in_service"
        assert api_time(before - timedelta(seconds=1)) <= back["occurred_at"] <= api_time(
            now_ist() + timedelta(seconds=1))

    def test_by_an_operator_naming_himself(self, at_site, machine):
        client, person = at_site("maint_operator")
        res = self.raise_fixed(client, machine, {"person_id": person["id"]})
        assert res.status_code == 201, res.get_json()
        assert res.get_json()["state"] == "back_in_service"

    def test_a_storekeeper_cannot_raise_at_all(self, role_client, eng, machine, nothing_written):
        res = self.raise_fixed(role_client("maint_storekeeper"), machine, {"person_id": eng[1]["id"]})
        assert res.status_code == 403

    def test_without_a_person_is_400(self, admin, machine, nothing_written):
        res = self.raise_fixed(admin, machine, {})
        assert refusal(res) == (400, "restore.person_id", "Who did the work? Pick a name")

    def test_a_person_from_another_site_is_400(self, admin, make_person, make_site, give_site_role, machine,
                                               nothing_written):
        person = make_person()
        give_site_role(person, make_site())
        res = self.raise_fixed(admin, machine, {"person_id": person["id"]})
        assert refusal(res) == (400, "restore.person_id", "Choose a person from this site")

    def test_back_in_service_before_the_raise_is_400(self, admin, eng, machine, nothing_written):
        failed_at = now_ist().replace(second=0, microsecond=0) - timedelta(hours=2)
        res = self.raise_fixed(admin, machine, {"person_id": eng[1]["id"],
                                                "occurred_at": local(failed_at - timedelta(minutes=5))},
                               occurred_at=local(failed_at))
        assert refusal(res) == (400, "restore.occurred_at", f"Must be at or after the time it happened, {failed_at:%d-%m-%Y %H:%M}")

    @pytest.mark.parametrize("offset", [-5, 50])
    def test_a_start_outside_raise_and_back_in_service_is_400(self, admin, eng, machine, nothing_written, offset):
        failed_at = now_ist().replace(second=0, microsecond=0) - timedelta(hours=2)
        res = self.raise_fixed(admin, machine, {"person_id": eng[1]["id"],
                                                "occurred_at": local(failed_at + timedelta(minutes=45)),
                                                "started_at": local(failed_at + timedelta(minutes=offset))},
                               occurred_at=local(failed_at))
        assert refusal(res)[:2] == (400, "restore.started_at")

    def test_closes_through_the_ordinary_close(self, admin, eng, machine, cause, action, noise):
        _, person = eng
        ticket = self.raise_fixed(admin, machine, {"person_id": person["id"]}).get_json()
        assert move_names(detail(admin, ticket)) == ["send-back", "close"]
        close = {"cause_id": cause, "action_id": action, "failure_mode_id": noise}
        assert move(admin, ticket, "close", **close).status_code == 409
        booked(admin, ticket, person)
        assert moved(admin, ticket, "close", **close)["state"] == "closed"
