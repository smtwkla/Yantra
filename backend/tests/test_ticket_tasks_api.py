"""Tasks on a ticket (S106 § 8.3), against the test DB.  Needs the dev MariaDB container
(tooling/dev/dev-db-up.bat).

ticket:assign adds, changes and cancels a task; its owner (by data) or a ticket:assign holder at the ticket's
site marks it done; an open task blocks Close and Not a fault.  The people have real memberships at the
ticket's site (user_at_sites), because the X-Test-Role wildcard holds at every site.  Each test makes its own
machine and ticket, and finds a task by its id or text, never by its place in a shared list.
"""

from datetime import timedelta

import pytest

from tests.conftest import EQUIPMENT, MASTERS
from tests.ticket_helpers import local, now_ist, refusal
from tests.test_ticket_work_api import booked, detail, move, moved, scheduled, url
from ticket_tasks_core import (
    ALREADY_CANCELLED, ALREADY_DONE, DONE_NOT_CANCELLED, ONLY_OPEN_CHANGES, OWNER_OR_ASSIGNER, TASKS_FULL,
    TASKS_MAX, WAS_CANCELLED, close_block,
)
from tickets import PERSON_AT_SITE, TICKET_CLOSED

OPEN_STATES = ("raised", "acknowledged", "scheduled", "in_progress", "back_in_service")


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def site(unit):
    return {"id": unit["site_id"]}


@pytest.fixture
def at_site(user_at_sites, site, unit):
    """at_site(role) -> (client, person): a user with a Team record holding ``role`` at the ticket's site, on
    its unit."""
    return lambda role: user_at_sites([(site, role, [unit])])


@pytest.fixture
def tech(at_site):
    return at_site("maint_technician")


@pytest.fixture
def eng(at_site):
    return at_site("maint_engineer")


@pytest.fixture
def fitter(make_person, give_site_role, site):
    """A technician of the site without a login (a contractor's fitter)."""
    person = make_person(name="Fitter without phone")
    give_site_role(person, site, "maint_technician")
    return person


@pytest.fixture
def ticket(make_ticket, machine):
    """A ticket that happened a day ago, so a done time an hour ago is after it."""
    return make_ticket(machine, occurred_at=local(now_ist() - timedelta(days=1)))


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


def today():
    return now_ist().date()


def body(owner, text="Check the space heater circuit and find any fuse", due=None, **overrides):
    return {"text": text, "owner_id": owner["id"], "due_date": (due or today() + timedelta(days=2)).isoformat(),
            **overrides}


def add(client, ticket, owner, **kwargs):
    return client.post(url(ticket, "tasks"), json=body(owner, **kwargs))


def added(client, ticket, owner, **kwargs):
    """Add a task -> ``(the detail, the new task)``: the task is the one with the highest id."""
    res = add(client, ticket, owner, **kwargs)
    assert res.status_code == 201, res.get_json()
    page = res.get_json()
    return page, max(page["tasks"], key=lambda task: task["id"])


def task_url(ticket, task, *parts):
    return url(ticket, "tasks", str(task["id"]), *parts)


def done(client, ticket, task, **extra):
    return client.post(task_url(ticket, task, "done"), json={"done_text": "Fuse F2 blown, replaced", **extra})


def cancel(client, ticket, task, reason="Moved to the improvement"):
    return client.post(task_url(ticket, task, "cancel"), json={"reason": reason})


def change(client, ticket, task, **fields):
    return client.put(task_url(ticket, task), json=fields)


def task_in(page, task):
    return next(t for t in page["tasks"] if t["id"] == task["id"])


def task_events(page, task):
    return [e for e in page["events"] if e["task_id"] == task["id"]]


def stored(db_rows, task):
    return db_rows("SELECT * FROM ticket_tasks WHERE id = %s", (task["id"],))[0]


def event_count(db_rows, ticket):
    return db_rows("SELECT COUNT(*) AS n FROM ticket_events WHERE ticket_id = %s", (ticket["id"],))[0]["n"]


def mine(client):
    res = client.get("/api/tickets/tasks/mine")
    assert res.status_code == 200, res.get_json()
    return res.get_json()


def close_body(cause, action, noise):
    return {"cause_id": cause, "action_id": action, "failure_mode_id": noise}


# ---------------------------------------------------------------------------
# Add
# ---------------------------------------------------------------------------

class TestAdd:

    def test_an_engineer_adds_a_task(self, eng, tech, ticket):
        client, eng_person = eng
        _, tech_person = tech
        page, task = added(client, ticket, tech_person)
        assert task["text"] == "Check the space heater circuit and find any fuse"
        assert task["state"] == "open" and task["overdue_days"] == 0
        assert task["due_date"] == (today() + timedelta(days=2)).isoformat()
        assert task["owner"]["id"] == tech_person["id"] and task["owner"]["has_login"] is True
        assert task["created_by_name"] == eng_person["name"]
        assert task["done_at"] is None and task["updated_at"] is None
        assert page["task_counts"] == {"open": 1, "done": 0, "cancelled": 0, "overdue": 0}

    def test_an_owner_without_a_login_and_an_operator(self, eng, at_site, fitter, ticket):
        client, _ = eng
        _, fitter_task = added(client, ticket, fitter)
        assert fitter_task["owner"]["has_login"] is False
        _, operator = at_site("maint_operator")
        _, operator_task = added(client, ticket, operator)
        assert operator_task["owner"]["id"] == operator["id"]

    def test_the_owner_must_be_an_active_member_of_the_site(self, eng, make_person, give_site_role, make_site,
                                                            site, db_rows, ticket):
        client, _ = eng
        gone = make_person(name="Left the plant")
        give_site_role(gone, site, "maint_technician")
        db_rows("UPDATE people SET active = 0 WHERE id = %s", (gone["id"],))
        elsewhere = make_person(name="Other site")
        give_site_role(elsewhere, make_site(), "maint_technician")
        for person in (gone, elsewhere):
            assert refusal(add(client, ticket, person)) == (400, "owner_id", PERSON_AT_SITE)

    def test_the_due_date_window(self, eng, tech, ticket):
        client, _ = eng
        _, person = tech
        happened = today() - timedelta(days=1)
        res = add(client, ticket, person, due=happened - timedelta(days=1))
        assert refusal(res) == (400, "due_date",
                                f"Choose a date from {happened:%d-%m-%Y}, the day the problem happened")
        assert refusal(add(client, ticket, person, due=today() + timedelta(days=366))) == (
            400, "due_date", "Choose a date within a year")
        # Back to the day it happened, and a year ahead, are allowed
        added(client, ticket, person, due=happened)
        added(client, ticket, person, due=today() + timedelta(days=365))

    def test_a_bad_body_is_400(self, eng, tech, ticket):
        client, _ = eng
        _, person = tech
        assert refusal(client.post(url(ticket, "tasks"), json={})) == (400, "text", "Enter what to do")
        assert refusal(add(client, ticket, person, due_date="22-11-2026"))[:2] == (400, "due_date")

    def test_the_31st_task_is_refused(self, eng, tech, ticket, db_rows):
        client, _ = eng
        _, person = tech
        for _n in range(TASKS_MAX - 1):
            db_rows("INSERT INTO ticket_tasks (ticket_id, text, owner_id, due_date, state, cancel_reason,"
                    " cancelled_at, cancelled_by, created_by) VALUES (%s, 'Old', %s, %s, 'cancelled', 'No',"
                    " NOW(), 'kla', 'kla')", (ticket["id"], person["id"], today()))
        added(client, ticket, person)
        assert refusal(add(client, ticket, person)) == (409, None, TASKS_FULL)

    def test_who_may_add(self, tech, user_at_sites, make_site, make_unit, site, unit, admin, ticket):
        tech_client, person = tech
        assert add(tech_client, ticket, person).status_code == 403
        other_site = make_site()
        elsewhere, _ = user_at_sites([(other_site, "maint_engineer", "all")])
        assert add(elsewhere, ticket, person).status_code == 404
        here_operator, _ = user_at_sites([(site, "maint_operator", [unit]),
                                          (other_site, "maint_engineer", "all")])
        assert add(here_operator, ticket, person).status_code == 403
        assert add(admin, ticket, person).status_code == 201

    @pytest.mark.parametrize("state", OPEN_STATES)
    def test_every_state_but_closed(self, eng, tech, ticket, set_ticket_state, state):
        client, _ = eng
        _, person = tech
        if state == "scheduled":
            scheduled(client, ticket)     # chk_tickets_plan: a scheduled row carries its plan
        else:
            set_ticket_state(ticket, state)
        assert add(client, ticket, person).status_code == 201

    def test_a_closed_ticket_takes_no_task(self, eng, tech, ticket, set_ticket_state):
        client, _ = eng
        _, person = tech
        set_ticket_state(ticket, "closed")
        assert refusal(add(client, ticket, person)) == (409, None, TICKET_CLOSED)


# ---------------------------------------------------------------------------
# Change
# ---------------------------------------------------------------------------

class TestChange:

    def test_each_field_alone(self, eng, tech, fitter, ticket):
        client, _ = eng
        _, person = tech
        _, task = added(client, ticket, person)
        res = change(client, ticket, task, text="Check the heater fuse")
        assert res.status_code == 200, res.get_json()
        assert task_in(res.get_json(), task)["text"] == "Check the heater fuse"
        res = change(client, ticket, task, owner_id=fitter["id"])
        assert task_in(res.get_json(), task)["owner"]["id"] == fitter["id"]
        new_due = today() + timedelta(days=5)
        res = change(client, ticket, task, due_date=new_due.isoformat())
        changed = task_in(res.get_json(), task)
        assert changed["due_date"] == new_due.isoformat() and changed["updated_at"] is not None
        assert [e["remark"] for e in task_events(res.get_json(), task)][1:] == [
            "What to do: Check the space heater circuit and find any fuse → Check the heater fuse",
            f"Owner: {person['name']} → {fitter['name']}",
            f"Due: {today() + timedelta(days=2):%d-%m-%Y} → {new_due:%d-%m-%Y}"]

    def test_an_owner_of_the_same_name_keeps_both_in_the_line(self, eng, make_person, give_site_role, site, ticket):
        client, _ = eng
        first = make_person(name="Same Name")
        second = make_person(name="Same Name")
        for person in (first, second):
            give_site_role(person, site, "maint_technician")
        _, task = added(client, ticket, first)
        page = change(client, ticket, task, owner_id=second["id"]).get_json()
        assert task_events(page, task)[-1]["remark"] == (
            f"Owner: Same Name (person {first['id']}) → Same Name (person {second['id']})")

    def test_nothing_changed_writes_nothing(self, eng, tech, ticket, db_rows):
        client, _ = eng
        _, person = tech
        _, task = added(client, ticket, person)
        events = event_count(db_rows, ticket)
        for fields in ({}, {"text": task["text"], "owner_id": person["id"], "due_date": task["due_date"]}):
            assert change(client, ticket, task, **fields).status_code == 200
        assert stored(db_rows, task)["updated_at"] is None
        assert event_count(db_rows, ticket) == events

    def test_an_owner_who_left_stays_until_sent_anew(self, eng, fitter, site, admin, ticket):
        client, _ = eng
        _, task = added(client, ticket, fitter)
        assert admin.delete(f"{MASTERS}/people/{fitter['id']}/sites/{site['id']}").status_code == 200
        res = change(client, ticket, task, text="Check the heater again", owner_id=fitter["id"])
        assert res.status_code == 200
        kept = task_in(res.get_json(), task)
        assert kept["owner"]["id"] == fitter["id"] and kept["owner"]["may_own"] is False
        assert kept["text"] == "Check the heater again"
        _, second = added(client, ticket, eng[1])
        assert refusal(change(client, ticket, second, owner_id=fitter["id"])) == (400, "owner_id", PERSON_AT_SITE)

    def test_a_done_or_cancelled_task_is_not_changed(self, eng, tech, ticket):
        client, _ = eng
        _, person = tech
        _, first = added(client, ticket, person)
        _, second = added(client, ticket, person)
        assert done(client, ticket, first).status_code == 200
        assert cancel(client, ticket, second).status_code == 200
        for task in (first, second):
            assert refusal(change(client, ticket, task, text="Again")) == (409, None, ONLY_OPEN_CHANGES)

    def test_a_task_of_another_ticket_is_not_found(self, eng, tech, make_ticket, machine, ticket):
        client, _ = eng
        _, person = tech
        _, task = added(client, ticket, person)
        other = make_ticket(machine)
        assert change(client, other, task, text="Again").status_code == 404
        assert done(client, other, task).status_code == 404
        assert cancel(client, other, task).status_code == 404


# ---------------------------------------------------------------------------
# Mark done
# ---------------------------------------------------------------------------

class TestMarkDone:

    def test_the_owner_marks_their_own(self, eng, tech, ticket, db_rows):
        client, _ = eng
        tech_client, person = tech
        _, task = added(client, ticket, person)
        res = done(tech_client, ticket, task)
        assert res.status_code == 200, res.get_json()
        finished = task_in(res.get_json(), task)
        assert finished["state"] == "done" and finished["done_text"] == "Fuse F2 blown, replaced"
        assert finished["done_by_name"] == person["name"] and finished["updated_at"] is None
        row = stored(db_rows, task)
        assert row["done_by"] == person["username"] and row["updated_at"] is None

    def test_a_technician_who_is_not_the_owner_is_refused(self, eng, at_site, fitter, ticket, db_rows):
        client, _ = eng
        other, _ = at_site("maint_technician")
        _, task = added(client, ticket, fitter)
        assert refusal(done(other, ticket, task)) == (403, None, OWNER_OR_ASSIGNER)
        assert stored(db_rows, task)["state"] == "open"

    def test_the_engineer_marks_it_for_an_owner_without_a_login(self, eng, fitter, ticket):
        client, eng_person = eng
        _, task = added(client, ticket, fitter)
        finished = task_in(done(client, ticket, task).get_json(), task)
        assert finished["done_by_name"] == eng_person["name"] and finished["owner"]["name"] == fitter["name"]

    def test_the_done_time(self, eng, fitter, ticket, db_rows):
        client, _ = eng
        _, task = added(client, ticket, fitter)
        assert refusal(done(client, ticket, task, done_at=local(now_ist() + timedelta(hours=1)))) == (
            400, "done_at", "That time is in the future")
        happened = db_rows("SELECT occurred_at FROM tickets WHERE id = %s", (ticket["id"],))[0]["occurred_at"]
        assert refusal(done(client, ticket, task, done_at=local(happened - timedelta(hours=1)))) == (
            400, "done_at", f"Not before the problem happened, {happened:%d-%m-%Y %H:%M}")
        an_hour_ago = (now_ist() - timedelta(hours=1)).replace(second=0, microsecond=0)
        page = done(client, ticket, task, done_at=local(an_hour_ago)).get_json()
        assert stored(db_rows, task)["done_at"] == an_hour_ago
        (line,) = [e for e in task_events(page, task) if e["event"] == "task_done"]
        assert line["occurred_at"] == an_hour_ago.strftime("%Y-%m-%dT%H:%M:%S+05:30")

    def test_states_and_body(self, eng, fitter, ticket):
        client, _ = eng
        _, first = added(client, ticket, fitter)
        _, second = added(client, ticket, fitter)
        assert refusal(client.post(task_url(ticket, first, "done"), json={})) == (400, "done_text",
                                                                                  "Say what you did")
        assert done(client, ticket, first).status_code == 200
        assert refusal(done(client, ticket, first)) == (409, None, ALREADY_DONE)
        assert cancel(client, ticket, second).status_code == 200
        assert refusal(done(client, ticket, second)) == (409, None, WAS_CANCELLED)

    def test_an_owner_removed_from_the_site_is_refused(self, eng, tech, site, admin, ticket):
        client, _ = eng
        tech_client, person = tech
        _, task = added(client, ticket, person)
        assert admin.delete(f"{MASTERS}/people/{person['id']}/sites/{site['id']}").status_code == 200
        # The owner's only membership is gone: ticket:read is held nowhere, so the route's key refuses
        assert done(tech_client, ticket, task).status_code == 403
        assert admin.post(task_url(ticket, task, "done"), json={"done_text": "Done for him"}).status_code == 200

    def test_it_admin_marks_done(self, eng, fitter, admin, ticket):
        client, _ = eng
        _, task = added(client, ticket, fitter)
        assert task_in(done(admin, ticket, task).get_json(), task)["state"] == "done"


class TestOwnerRuleEdges:

    def test_an_owner_whose_units_do_not_cover_the_ticket(self, eng, user_at_sites, make_unit, site, ticket,
                                                          db_rows):
        client, _ = eng
        other_unit = make_unit(site=site)
        owner_client, owner = user_at_sites([(site, "maint_technician", [other_unit])])
        _, task = added(client, ticket, owner)
        assert done(owner_client, ticket, task).status_code == 404
        assert stored(db_rows, task)["state"] == "open"
        assert task["id"] not in [item["id"] for item in mine(owner_client)["items"]]
        seen = task_in(detail(client, ticket), task)
        assert seen["owner"]["can_open"] is False and seen["owner"]["may_own"] is True

    def test_an_owner_who_sees_the_ticket_only_through_the_moved_machine(self, eng, user_at_sites, make_site,
                                                                         make_unit, admin, site, machine, ticket,
                                                                         db_rows):
        client, _ = eng
        other_site = make_site()
        other_unit = make_unit(site=other_site)
        owner_client, owner = user_at_sites([(site, "maint_storekeeper", "all"),
                                             (other_site, "maint_technician", [other_unit])])
        _, task = added(client, ticket, owner)
        assert admin.put(f"{EQUIPMENT}/{machine['id']}", json={"unit_id": other_unit["id"]}).status_code == 200
        assert owner_client.get(url(ticket)).status_code == 200
        (item,) = [item for item in mine(owner_client)["items"] if item["id"] == task["id"]]
        assert item["can_mark_done"] is False
        assert done(owner_client, ticket, task).status_code == 403
        assert stored(db_rows, task)["state"] == "open"


# ---------------------------------------------------------------------------
# Cancel
# ---------------------------------------------------------------------------

class TestCancel:

    def test_cancel_and_its_refusals(self, eng, tech, ticket):
        client, _ = eng
        tech_client, person = tech
        _, first = added(client, ticket, person)
        _, second = added(client, ticket, person)
        assert refusal(client.post(task_url(ticket, first, "cancel"), json={})) == (
            400, "reason", "Say why it is cancelled")
        assert cancel(tech_client, ticket, first).status_code == 403
        page = cancel(client, ticket, first).get_json()
        cancelled = task_in(page, first)
        assert cancelled["state"] == "cancelled" and cancelled["cancel_reason"] == "Moved to the improvement"
        assert cancelled["cancelled_by_name"] is not None
        assert refusal(cancel(client, ticket, first)) == (409, None, ALREADY_CANCELLED)
        assert done(client, ticket, second).status_code == 200
        assert refusal(cancel(client, ticket, second)) == (409, None, DONE_NOT_CANCELLED)


# ---------------------------------------------------------------------------
# What the four writes share (§ 5.1): the key at the site, the predicate, the closed ticket
# ---------------------------------------------------------------------------

class TestSharedRefusals:
    WRITES = ("add", "change", "done", "cancel")

    @staticmethod
    def write(name, client, ticket, task, owner):
        return {"add": lambda: add(client, ticket, owner), "change": lambda: change(client, ticket, task, text="X"),
                "done": lambda: done(client, ticket, task), "cancel": lambda: cancel(client, ticket, task),
                }[name]()

    @pytest.mark.parametrize("name", WRITES)
    def test_who_may_write(self, name, eng, tech, fitter, user_at_sites, make_site, site, unit, ticket, db_rows):
        client, _ = eng
        tech_client, _ = tech
        _, task = added(client, ticket, fitter)
        other_site = make_site()
        elsewhere, _ = user_at_sites([(other_site, "maint_engineer", "all")])
        here_operator, _ = user_at_sites([(site, "maint_operator", [unit]), (other_site, "maint_engineer", "all")])
        # A technician is not the task's owner, so mark done refuses on the owner rule (also 403)
        assert self.write(name, tech_client, ticket, task, fitter).status_code == 403
        # An engineer of another site cannot see the ticket; an operator here, engineer elsewhere, lacks the key here
        assert self.write(name, elsewhere, ticket, task, fitter).status_code == 404
        assert self.write(name, here_operator, ticket, task, fitter).status_code == 403
        assert stored(db_rows, task)["state"] == "open" and stored(db_rows, task)["text"] == task["text"]

    def test_a_closed_ticket_comes_before_the_task_state(self, eng, fitter, ticket, set_ticket_state):
        client, _ = eng
        _, finished = added(client, ticket, fitter)
        _, dropped = added(client, ticket, fitter)
        assert done(client, ticket, finished).status_code == 200
        assert cancel(client, ticket, dropped).status_code == 200
        set_ticket_state(ticket, "closed")
        for task in (finished, dropped):
            assert refusal(change(client, ticket, task, text="Again")) == (409, None, TICKET_CLOSED)
            assert refusal(done(client, ticket, task)) == (409, None, TICKET_CLOSED)
            assert refusal(cancel(client, ticket, task)) == (409, None, TICKET_CLOSED)


# ---------------------------------------------------------------------------
# The close
# ---------------------------------------------------------------------------

class TestClose:

    def test_an_open_task_blocks_close_until_done_or_cancelled(self, eng, fitter, restored, cause, action,
                                                               noise, db_rows):
        client, _ = eng
        _, first = added(client, restored, fitter)
        _, second = added(client, restored, fitter)
        page = detail(client, restored)
        (close,) = [m for m in page["moves"] if m["name"] == "close"]
        assert close["blocked_reason"] == close_block(2)
        events = event_count(db_rows, restored)
        assert refusal(move(client, restored, "close", **close_body(cause, action, noise))) == (
            409, None, close_block(2))
        assert db_rows("SELECT state FROM tickets WHERE id = %s", (restored["id"],))[0]["state"] == "back_in_service"
        assert event_count(db_rows, restored) == events
        done(client, restored, first)
        assert refusal(move(client, restored, "close", **close_body(cause, action, noise)))[2] == close_block(1)
        page = cancel(client, restored, second).get_json()
        (close,) = [m for m in page["moves"] if m["name"] == "close"]
        assert close["blocked_reason"] is None
        assert "blocked_reason" not in [m for m in page["moves"] if m["name"] == "send-back"][0]
        assert moved(client, restored, "close", **close_body(cause, action, noise))["state"] == "closed"

    def test_not_a_fault_is_blocked_too(self, eng, fitter, ticket, no_cause):
        client, _ = eng
        _, task = added(client, ticket, fitter)
        not_a_fault = {"cause_id": no_cause, "remark": "Operator error"}
        assert refusal(move(client, ticket, "not-a-fault", **not_a_fault)) == (409, None, close_block(1))
        (entry,) = [m for m in detail(client, ticket)["moves"] if m["name"] == "not-a-fault"]
        assert entry["blocked_reason"] == close_block(1)
        # Brief § 8.3: Back in service carries no such key (the other test checks send-back)
        (restore,) = [m for m in detail(client, ticket)["moves"] if m["name"] == "restore"]
        assert "blocked_reason" not in restore
        done(client, ticket, task)
        assert moved(client, ticket, "not-a-fault", **not_a_fault)["state"] == "closed"

    def test_back_in_service_is_never_blocked(self, eng, fitter, admin, ticket):
        client, eng_person = eng
        added(client, ticket, fitter)
        moved(admin, ticket, "start")
        page = moved(admin, ticket, "restore", person_id=eng_person["id"])
        assert page["state"] == "back_in_service" and page["task_counts"]["open"] == 1


# ---------------------------------------------------------------------------
# Timeline
# ---------------------------------------------------------------------------

class TestTimeline:

    def test_each_write_adds_one_line(self, eng, tech, fitter, restored, db_rows):
        client, _ = eng
        _, person = tech
        before = detail(client, restored)["times"]
        count = event_count(db_rows, restored)
        due = today() + timedelta(days=2)
        page, task = added(client, restored, person, due=due)
        assert event_count(db_rows, restored) == count + 1
        (line,) = task_events(page, task)
        assert (line["event"], line["remark"]) == (
            "task_added", f"{task['text']}\nOwner: {person['name']}. Due {due:%d-%m-%Y}.")
        new_due = due + timedelta(days=1)
        page = change(client, restored, task, text="Check the fuse", owner_id=fitter["id"],
                      due_date=new_due.isoformat()).get_json()
        assert event_count(db_rows, restored) == count + 2
        assert task_events(page, task)[-1]["event"] == "task_changed"
        assert task_events(page, task)[-1]["remark"].split("\n") == [
            f"What to do: {task['text']} → Check the fuse", f"Owner: {person['name']} → {fitter['name']}",
            f"Due: {due:%d-%m-%Y} → {new_due:%d-%m-%Y}"]
        page = done(client, restored, task).get_json()
        assert event_count(db_rows, restored) == count + 3
        assert [(e["event"], e["remark"]) for e in task_events(page, task)][-1] == (
            "task_done", "Fuse F2 blown, replaced")
        _, second = added(client, restored, person)
        page = cancel(client, restored, second).get_json()
        assert [(e["event"], e["remark"]) for e in task_events(page, second)] == [
            ("task_added", f"{second['text']}\nOwner: {person['name']}. Due {due:%d-%m-%Y}."),
            ("task_cancelled", "Moved to the improvement")]
        assert event_count(db_rows, restored) == count + 5
        assert all(e["task_id"] is None for e in page["events"] if not e["event"].startswith("task_"))
        assert page["times"] == before


# ---------------------------------------------------------------------------
# Detail
# ---------------------------------------------------------------------------

class TestDetail:

    def test_no_task(self, eng, ticket):
        page = detail(eng[0], ticket)
        assert page["tasks"] == []
        assert page["task_counts"] == {"open": 0, "done": 0, "cancelled": 0, "overdue": 0}
        assert page["can_add_task"] is True

    def test_overdue_and_counts(self, eng, fitter, ticket, db_rows):
        client, _ = eng
        _, late = added(client, ticket, fitter)
        _, finished = added(client, ticket, fitter)
        _, dropped = added(client, ticket, fitter)
        done(client, ticket, finished)
        cancel(client, ticket, dropped)
        db_rows("UPDATE ticket_tasks SET due_date = %s WHERE id IN (%s, %s)",
                (today() - timedelta(days=2), late["id"], finished["id"]))
        page = detail(client, ticket)
        assert [t["id"] for t in page["tasks"]] == sorted(t["id"] for t in page["tasks"])
        assert task_in(page, late)["overdue_days"] == 2
        assert task_in(page, finished)["overdue_days"] == 0
        assert page["task_counts"] == {"open": 1, "done": 1, "cancelled": 1, "overdue": 1}

    def test_the_flags(self, eng, tech, at_site, ticket, set_ticket_state):
        client, _ = eng
        tech_client, person = tech
        operator_client, _ = at_site("maint_operator")
        _, task = added(client, ticket, person)
        engineer_view = task_in(detail(client, ticket), task)
        assert (engineer_view["can_change"], engineer_view["can_mark_done"]) == (True, True)
        owner_page = detail(tech_client, ticket)
        owner_view = task_in(owner_page, task)
        assert (owner_view["can_change"], owner_view["can_mark_done"]) == (False, True)
        assert owner_page["can_add_task"] is False
        operator_view = task_in(detail(operator_client, ticket), task)
        assert (operator_view["can_change"], operator_view["can_mark_done"]) == (False, False)
        set_ticket_state(ticket, "closed")
        closed_page = detail(client, ticket)
        assert closed_page["can_add_task"] is False
        assert (task_in(closed_page, task)["can_change"], task_in(closed_page, task)["can_mark_done"]) == (
            False, False)

    def test_may_own_after_the_membership_is_removed(self, eng, fitter, site, admin, ticket):
        client, _ = eng
        _, task = added(client, ticket, fitter)
        assert task["owner"]["may_own"] is True and task["owner"]["active"] is True
        assert admin.delete(f"{MASTERS}/people/{fitter['id']}/sites/{site['id']}").status_code == 200
        assert task_in(detail(client, ticket), task)["owner"]["may_own"] is False

    def test_can_open(self, eng, tech, fitter, user_at_sites, site, ticket):
        client, _ = eng
        _, person = tech
        _, storekeeper = user_at_sites([(site, "maint_storekeeper", "all")])
        _, with_login = added(client, ticket, person)
        _, without_login = added(client, ticket, fitter)
        page, keeper = added(client, ticket, storekeeper)
        assert task_in(page, with_login)["owner"]["can_open"] is True
        assert task_in(page, without_login)["owner"]["can_open"] is False
        assert task_in(page, keeper)["owner"]["can_open"] is False
        assert task_in(page, keeper)["owner"]["has_login"] is True

    def test_events_carry_task_id(self, eng, ticket):
        page = detail(eng[0], ticket)
        assert all("task_id" in e and e["task_id"] is None for e in page["events"])


# ---------------------------------------------------------------------------
# Mine
# ---------------------------------------------------------------------------

class TestMine:

    def test_my_open_tasks_by_due_date(self, eng, tech, fitter, ticket):
        client, _ = eng
        tech_client, person = tech
        _, later = added(client, ticket, person, due=today() + timedelta(days=5))
        _, sooner = added(client, ticket, person, due=today() + timedelta(days=1))
        _, finished = added(client, ticket, person)
        _, dropped = added(client, ticket, person)
        added(client, ticket, fitter)
        done(client, ticket, finished)
        cancel(client, ticket, dropped)
        result = mine(tech_client)
        assert [item["id"] for item in result["items"]] == [sooner["id"], later["id"]]
        assert result["total"] == 2
        item = result["items"][0]
        assert item["can_mark_done"] is True and item["overdue_days"] == 0
        assert item["ticket"]["id"] == ticket["id"] and item["ticket"]["serial"] == ticket["serial"]
        assert item["ticket"]["machine"]["id"] == ticket["machine"]["id"]

    def test_it_admin_without_a_team_record_owns_none(self, admin):
        assert mine(admin) == {"items": [], "total": 0}

    def test_an_operator_moved_off_the_unit_no_longer_sees_theirs(self, eng, at_site, make_unit, admin, site,
                                                                  ticket):
        client, _ = eng
        operator_client, operator = at_site("maint_operator")
        _, task = added(client, ticket, operator)
        assert [item["id"] for item in mine(operator_client)["items"]] == [task["id"]]
        other_unit = make_unit(site=site)
        res = admin.put(f"{MASTERS}/people/{operator['id']}/sites/{site['id']}",
                        json={"role": "maint_operator", "all_units": False, "unit_ids": [other_unit["id"]]})
        assert res.status_code == 200, res.get_json()
        assert mine(operator_client) == {"items": [], "total": 0}


# ---------------------------------------------------------------------------
# The database down
# ---------------------------------------------------------------------------

def test_the_database_down_is_503(eng, tech, ticket, db_down):
    client, _ = eng
    _, person = tech
    assert add(client, ticket, person).status_code == 503
