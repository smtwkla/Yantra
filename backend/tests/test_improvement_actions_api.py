"""Countermeasures (S070 § 8.2), against the test DB.  Needs the dev MariaDB container.

Each test starts its own improvement on its own ticket (S067's fixtures, imported from
test_improvements_api), so the kept worker database is the starting state.  The ticket is moved
two days back, so a due date or a done time in the past can be tried against the problem's time.
"Another site" and "a key missing here" as S067 § 8.2: a person with no membership at the
improvement's site (404), and one who is operator here and engineer at another site (403).
"""

from datetime import datetime, timedelta

import pytest

import improvements_core
from tests.conftest import MASTERS
from tests.test_improvements_api import (  # noqa: F401  (fixtures used by name)
    IMPROVEMENTS, eng, get, other_site, restored_ticket, site, started,
)
from tests.ticket_helpers import now_ist, refusal

MINE = f"{IMPROVEMENTS}/actions/mine"
OWNERS = f"{IMPROVEMENTS}/owners"
KINDS = ("correction", "corrective", "preventive", "design_out", "lesson", "spread")
OWNER_OR_EDITOR = "Only the owner, or an engineer or manager of this site, can do this"


@pytest.fixture
def made(eng, restored_ticket, db_rows):
    """An improvement whose ticket happened two days ago (the problem's time)."""
    client, person = eng
    ticket = restored_ticket()
    db_rows("UPDATE tickets SET occurred_at = %s WHERE id = %s",
            ((now_ist() - timedelta(days=2)).replace(second=0, microsecond=0), ticket["id"]))
    return started(client, ticket, person)


@pytest.fixture
def technician(user_at_sites, site):
    """(client, person): a technician of the site, holding improvement:read only."""
    return user_at_sites([(site, "maint_technician", "all")])


@pytest.fixture
def fitter(make_person, give_site_role, site):
    """A technician of the site without a login (the fitter without a phone)."""
    person = make_person(name="Fitter Murugan")
    give_site_role(person, site, "maint_technician")
    return person


@pytest.fixture
def operator(user_at_sites, site):
    return user_at_sites([(site, "maint_operator", "all")])


@pytest.fixture
def operator_here(user_at_sites, site, other_site):
    """Operator here, engineer elsewhere: the predicate passes, the key at the site does not (403)."""
    return user_at_sites([(site, "maint_operator", "all"), (other_site, "maint_engineer", "all")])[0]


@pytest.fixture
def stranger(user_at_sites, other_site):
    """An engineer of another site: the predicate hides the improvement (404)."""
    return user_at_sites([(other_site, "maint_engineer", "all")])[0]


def today():
    return now_ist().date()


def day(offset):
    return (today() + timedelta(days=offset)).isoformat()


def actions_url(improvement, action=None, suffix=""):
    base = f"{IMPROVEMENTS}/{improvement['id']}/actions"
    return base if action is None else f"{base}/{action['id']}{suffix}"


def add_action(client, improvement, owner, **overrides):
    body = {"kind": "corrective", "text": "Fit a sealed contact block", "owner_id": owner["id"],
            "due_date": day(7), **overrides}
    return client.post(actions_url(improvement), json=body)


def added(client, improvement, owner, **overrides):
    """-> the new countermeasure, as the detail shows it."""
    res = add_action(client, improvement, owner, **overrides)
    assert res.status_code == 201, res.get_json()
    return res.get_json()["actions"][-1]


def mark_done(client, improvement, action, done_text="Fitted the sealed block", **extra):
    return client.post(actions_url(improvement, action, "/done"), json={"done_text": done_text, **extra})


def cancel(client, improvement, action, reason="Duplicate of another countermeasure"):
    return client.post(actions_url(improvement, action, "/cancel"), json={"reason": reason})


def change(client, improvement, action, **fields):
    return client.put(actions_url(improvement, action), json=fields)


def the_action(detail, action):
    return next(a for a in detail["actions"] if a["id"] == action["id"])


def problem_at(detail):
    return datetime.strptime(detail["problem_at"], "%Y-%m-%dT%H:%M:%S+05:30")


# ---------------------------------------------------------------------------
# Add
# ---------------------------------------------------------------------------

class TestAdd:

    @pytest.mark.parametrize("kind", KINDS)
    def test_each_kind(self, eng, made, technician, kind):
        client, person = eng
        _, owner = technician
        action = added(client, made, owner, kind=kind)
        assert (action["kind"], action["state"], action["text"], action["due_date"]) == (
            kind, "open", "Fit a sealed contact block", day(7))
        assert action["created_by_name"] == person["name"]
        assert action["owner"] == {"id": owner["id"], "name": owner["name"], "active": True, "has_login": True,
                                   "may_own": True}
        assert (action["done_text"], action["done_at"], action["cancel_reason"], action["updated_at"]) == (
            None, None, None, None)

    def test_an_owner_without_a_login(self, eng, made, fitter):
        client, _ = eng
        action = added(client, made, fitter)
        assert action["owner"]["has_login"] is False and action["owner"]["name"] == "Fitter Murugan"

    def test_a_storekeeper_owns_it_and_the_engineer_marks_it_done(self, eng, made, user_at_sites, site):
        client, person = eng
        storekeeper_client, storekeeper = user_at_sites([(site, "maint_storekeeper", "all")])
        action = added(client, made, storekeeper, kind="preventive", text="Keep two spare contact blocks")
        # The storekeeper holds no improvement:read: they never see it (§ 5.3)
        assert storekeeper_client.get(f"{IMPROVEMENTS}/{made['id']}").status_code == 403
        res = mark_done(client, made, action, done_text="Two blocks on the shelf")
        assert res.status_code == 200, res.get_json()
        done = the_action(res.get_json(), action)
        assert (done["state"], done["done_by_name"], done["owner"]["name"]) == ("done", person["name"],
                                                                                storekeeper["name"])

    def test_an_owner_who_may_not_own_it(self, admin, eng, made, user_at_sites, site, other_site):
        client, _ = eng
        _, inactive = user_at_sites([(site, "maint_technician", "all")])
        assert admin.put(f"{MASTERS}/people/{inactive['id']}", json={"active": False}).status_code == 200
        _, elsewhere = user_at_sites([(other_site, "maint_technician", "all")])
        for owner in (inactive, elsewhere, {"id": 999999999}):
            assert refusal(add_action(client, made, owner)) == (400, "owner_id", "Choose a person of this site")

    def test_the_due_date_bounds(self, eng, made, technician):
        client, _ = eng
        _, owner = technician
        problem_day = problem_at(get(client, made)).date()
        assert added(client, made, owner, due_date=problem_day.isoformat())["due_date"] == problem_day.isoformat()
        before = problem_day - timedelta(days=1)
        assert refusal(add_action(client, made, owner, due_date=before.isoformat())) == (
            400, "due_date", f"Choose a date from {problem_day:%d-%m-%Y}, the day the problem happened")
        assert add_action(client, made, owner, due_date=day(365)).status_code == 201
        assert refusal(add_action(client, made, owner, due_date=day(366))) == (
            400, "due_date", "Choose a date within a year")
        assert refusal(add_action(client, made, owner, due_date="31-10-2026")) == (
            400, "due_date", "Enter the date as YYYY-MM-DD")

    def test_the_31st_is_409(self, eng, made, technician, db_rows):
        client, _ = eng
        _, owner = technician
        for _ in range(30):
            db_rows("INSERT INTO improvement_actions (improvement_id, kind, text, owner_id, due_date, created_by)"
                    " VALUES (%s, 'lesson', 'Teach it', %s, %s, 'kla')", (made["id"], owner["id"], day(7)))
        assert refusal(add_action(client, made, owner)) == (
            409, None, "An improvement holds up to 30 countermeasures. Change an open one instead.")

    def test_who_may_add(self, operator, operator_here, stranger, eng, made, technician):
        _, owner = technician
        assert add_action(operator[0], made, owner).status_code == 403
        assert add_action(operator_here, made, owner).status_code == 403
        assert add_action(stranger, made, owner).status_code == 404
        assert add_action(technician[0], made, owner).status_code == 403
        assert add_action(eng[0], {"id": 999999999}, owner).status_code == 404

    def test_a_missing_field_is_400(self, eng, made, technician):
        client, _ = eng
        _, owner = technician
        assert refusal(add_action(client, made, owner, kind="kaizen")) == (400, "kind", "Choose the kind")
        assert refusal(add_action(client, made, owner, text="  ")) == (400, "text", "Enter what will be done")

    def test_a_closed_improvement_is_409(self, monkeypatch, eng, made, technician):
        """Every improvement is open until R05.4: the check is proved with no open state."""
        monkeypatch.setattr(improvements_core, "IMPROVEMENT_OPEN_STATES", ())
        client, _ = eng
        assert refusal(add_action(client, made, technician[1])) == (409, None, "This improvement is closed")

    def test_the_database_down_is_503(self, eng, made, technician, db_down):
        client, _ = eng
        assert add_action(client, made, technician[1]).status_code == 503


# ---------------------------------------------------------------------------
# Change
# ---------------------------------------------------------------------------

class TestChange:

    def test_each_field(self, eng, made, technician, fitter):
        client, person = eng
        action = added(client, made, technician[1])
        res = change(client, made, action, kind="design_out", text="Fit a sealed panel", owner_id=fitter["id"],
                     due_date=day(10))
        assert res.status_code == 200, res.get_json()
        changed = the_action(res.get_json(), action)
        assert (changed["kind"], changed["text"], changed["owner"]["id"], changed["due_date"]) == (
            "design_out", "Fit a sealed panel", fitter["id"], day(10))
        assert changed["updated_at"] is not None

    def test_no_change_writes_nothing(self, eng, made, technician, db_rows):
        client, _ = eng
        action = added(client, made, technician[1])
        res = change(client, made, action, kind="corrective", text="Fit a sealed contact block",
                     owner_id=technician[1]["id"], due_date=day(7))
        assert res.status_code == 200
        assert db_rows("SELECT updated_at FROM improvement_actions WHERE id = %s", (action["id"],)) == [
            {"updated_at": None}]

    def test_an_owner_who_left_is_kept_unless_sent_anew(self, admin, eng, made, technician, user_at_sites, site):
        """Kept while unchanged (the same id sent again is no change); a new pick of a person
        who has left is refused."""
        client, _ = eng
        _, owner = technician
        _, leaver = user_at_sites([(site, "maint_technician", "all")])
        action = added(client, made, owner)
        for person in (owner, leaver):
            assert admin.delete(f"{MASTERS}/people/{person['id']}/sites/{site['id']}").status_code in (200, 204)
        res = change(client, made, action, text="Fit a sealed contact block now")
        assert res.status_code == 200
        kept = the_action(res.get_json(), action)
        assert kept["owner"]["id"] == owner["id"] and kept["owner"]["may_own"] is False
        assert change(client, made, action, owner_id=owner["id"]).status_code == 200
        assert refusal(change(client, made, action, owner_id=leaver["id"])) == (
            400, "owner_id", "Choose a person of this site")

    def test_a_new_owner_must_be_of_the_site(self, eng, made, technician, user_at_sites, other_site):
        client, _ = eng
        action = added(client, made, technician[1])
        _, elsewhere = user_at_sites([(other_site, "maint_technician", "all")])
        assert refusal(change(client, made, action, owner_id=elsewhere["id"])) == (
            400, "owner_id", "Choose a person of this site")

    def test_null_is_refused(self, eng, made, technician):
        client, _ = eng
        action = added(client, made, technician[1])
        assert refusal(change(client, made, action, kind=None)) == (400, "kind", "Choose the kind")

    def test_a_done_or_cancelled_one_is_409(self, eng, made, technician):
        client, _ = eng
        done = added(client, made, technician[1])
        assert mark_done(client, made, done).status_code == 200
        cancelled = added(client, made, technician[1])
        assert cancel(client, made, cancelled).status_code == 200
        for action in (done, cancelled):
            assert refusal(change(client, made, action, text="New")) == (
                409, None, "Only an open countermeasure can be changed")

    def test_who_may_change(self, eng, made, technician, operator_here, stranger):
        client, _ = eng
        action = added(client, made, technician[1])
        assert change(technician[0], made, action, text="Mine").status_code == 403
        assert change(operator_here, made, action, text="x").status_code == 403
        assert change(stranger, made, action, text="x").status_code == 404

    def test_a_countermeasure_of_another_improvement_is_404(self, eng, made, restored_ticket, technician):
        client, person = eng
        other = started(client, restored_ticket(), person)
        action = added(client, other, technician[1])
        assert change(client, made, action, text="x").status_code == 404
        assert change(client, made, {"id": 999999999}, text="x").status_code == 404


# ---------------------------------------------------------------------------
# Mark done
# ---------------------------------------------------------------------------

class TestMarkDone:

    def test_the_owner_marks_their_own(self, eng, made, technician, db_rows):
        client, _ = eng
        owner_client, owner = technician
        action = added(client, made, owner)
        res = mark_done(owner_client, made, action)
        assert res.status_code == 200, res.get_json()
        done = the_action(res.get_json(), action)
        assert (done["state"], done["done_text"], done["done_by_name"]) == ("done", "Fitted the sealed block",
                                                                            owner["name"])
        assert done["updated_at"] is None
        row = db_rows("SELECT done_by, done_at, updated_at FROM improvement_actions WHERE id = %s", (action["id"],))[0]
        assert row["done_by"] == owner_client._headers["X-Test-User"] and row["updated_at"] is None
        assert abs(row["done_at"] - now_ist()) < timedelta(minutes=1)

    def test_a_technician_who_is_not_the_owner_is_403(self, eng, made, technician, user_at_sites, site):
        client, _ = eng
        action = added(client, made, technician[1])
        other_client, _ = user_at_sites([(site, "maint_technician", "all")])
        assert refusal(mark_done(other_client, made, action)) == (403, None, OWNER_OR_EDITOR)

    def test_the_engineer_for_an_owner_without_a_login(self, eng, made, fitter):
        client, person = eng
        action = added(client, made, fitter)
        done = the_action(mark_done(client, made, action).get_json(), action)
        assert (done["state"], done["done_by_name"], done["owner"]["name"]) == ("done", person["name"],
                                                                                "Fitter Murugan")

    def test_done_at_an_hour_ago_is_stored(self, eng, made, technician, db_rows):
        client, _ = eng
        action = added(client, made, technician[1])
        hour_ago = (now_ist() - timedelta(hours=1)).replace(second=0, microsecond=0)
        res = mark_done(client, made, action, done_at=hour_ago.strftime("%Y-%m-%dT%H:%M"))
        assert res.status_code == 200, res.get_json()
        assert db_rows("SELECT done_at FROM improvement_actions WHERE id = %s", (action["id"],)) == [
            {"done_at": hour_ago}]

    def test_the_done_time_bounds(self, eng, made, technician):
        client, _ = eng
        action = added(client, made, technician[1])
        future = now_ist() + timedelta(minutes=10)
        assert refusal(mark_done(client, made, action, done_at=future.strftime("%Y-%m-%dT%H:%M"))) == (
            400, "done_at", "That time is in the future")
        problem = problem_at(get(client, made))
        before = problem - timedelta(minutes=1)
        assert refusal(mark_done(client, made, action, done_at=before.strftime("%Y-%m-%dT%H:%M"))) == (
            400, "done_at", f"Not before the problem happened, {problem:%d-%m-%Y %H:%M}")
        assert mark_done(client, made, action, done_at=problem.strftime("%Y-%m-%dT%H:%M")).status_code == 200

    def test_already_done_or_cancelled_is_409(self, eng, made, technician):
        client, _ = eng
        done = added(client, made, technician[1])
        assert mark_done(client, made, done).status_code == 200
        assert refusal(mark_done(client, made, done)) == (409, None, "This countermeasure is already done")
        cancelled = added(client, made, technician[1])
        assert cancel(client, made, cancelled).status_code == 200
        assert refusal(mark_done(client, made, cancelled)) == (409, None, "This countermeasure was cancelled")

    def test_a_missing_done_text_is_400(self, eng, made, technician):
        client, _ = eng
        action = added(client, made, technician[1])
        assert refusal(mark_done(client, made, action, done_text="  ")) == (400, "done_text", "Say what you did")

    def test_who_may_not(self, eng, made, technician, stranger, role_client):
        client, _ = eng
        action = added(client, made, technician[1])
        assert mark_done(stranger, made, action).status_code == 404
        assert mark_done(role_client("it_admin"), made, action).status_code == 403
        assert mark_done(role_client("maint_storekeeper"), made, action).status_code == 403


# ---------------------------------------------------------------------------
# Cancel
# ---------------------------------------------------------------------------

class TestCancel:

    def test_with_a_reason(self, eng, made, technician):
        client, person = eng
        action = added(client, made, technician[1])
        res = cancel(client, made, action)
        assert res.status_code == 200, res.get_json()
        cancelled = the_action(res.get_json(), action)
        assert (cancelled["state"], cancelled["cancel_reason"], cancelled["cancelled_by_name"]) == (
            "cancelled", "Duplicate of another countermeasure", person["name"])
        assert cancelled["cancelled_at"] is not None and cancelled["updated_at"] is None

    def test_refusals(self, eng, made, technician):
        client, _ = eng
        owner_client, owner = technician
        action = added(client, made, owner)
        assert refusal(cancel(client, made, action, reason="  ")) == (400, "reason", "Say why it is cancelled")
        assert cancel(owner_client, made, action).status_code == 403
        assert cancel(client, made, action).status_code == 200
        assert refusal(cancel(client, made, action)) == (409, None, "This countermeasure is already cancelled")
        done = added(client, made, owner)
        assert mark_done(client, made, done).status_code == 200
        assert refusal(cancel(client, made, done)) == (409, None, "A done countermeasure cannot be cancelled")


# ---------------------------------------------------------------------------
# The detail
# ---------------------------------------------------------------------------

class TestDetail:

    def test_actions_by_id_with_counts_and_overdue(self, eng, made, technician):
        client, _ = eng
        _, owner = technician
        late = added(client, made, owner, due_date=day(-2))
        on_time = added(client, made, owner, due_date=day(0))
        done = added(client, made, owner, due_date=day(-2))
        assert mark_done(client, made, done).status_code == 200
        cancelled = added(client, made, owner)
        detail = cancel(client, made, cancelled).get_json()
        assert [a["id"] for a in detail["actions"]] == [late["id"], on_time["id"], done["id"], cancelled["id"]]
        assert [a["overdue_days"] for a in detail["actions"]] == [2, 0, 0, 0]
        assert detail["action_counts"] == {"open": 2, "done": 1, "cancelled": 1, "overdue": 1}
        assert problem_at(detail).date() == today() - timedelta(days=2)

    def test_an_improvement_with_none(self, eng, made):
        detail = get(eng[0], made)
        assert (detail["actions"], detail["action_counts"]) == ([], {"open": 0, "done": 0, "cancelled": 0,
                                                                    "overdue": 0})

    def test_the_flags(self, eng, made, technician, operator):
        client, _ = eng
        owner_client, owner = technician
        action = added(client, made, owner)
        flags = ("can_change", "can_mark_done", "can_add_photo")
        assert [the_action(get(client, made), action)[f] for f in flags] == [True, True, True]
        assert [the_action(get(owner_client, made), action)[f] for f in flags] == [False, True, True]
        assert [the_action(get(operator[0], made), action)[f] for f in flags] == [False, False, False]
        assert mark_done(owner_client, made, action).status_code == 200
        assert [the_action(get(owner_client, made), action)[f] for f in flags] == [False, False, True]

    def test_documents_of_a_countermeasure(self, eng, made, technician):
        from tests.documents_helpers import JPEG, uploaded_to
        client, _ = eng
        action = added(client, made, technician[1])
        photo = uploaded_to(client, f"{IMPROVEMENTS}/actions/{action['id']}/documents", kind="photo", title="Fitted",
                            data=JPEG, filename="IMG_9.jpg")
        assert the_action(get(client, made), action)["documents"] == [
            {"id": photo["id"], "kind": "photo", "title": "Fitted", "has_thumb": True}]

    def test_may_own_false_after_the_membership_is_removed(self, admin, eng, made, technician, site):
        client, _ = eng
        _, owner = technician
        action = added(client, made, owner)
        assert admin.delete(f"{MASTERS}/people/{owner['id']}/sites/{site['id']}").status_code in (200, 204)
        assert the_action(get(client, made), action)["owner"]["may_own"] is False


# ---------------------------------------------------------------------------
# Mine
# ---------------------------------------------------------------------------

class TestMine:

    def test_the_owners_open_ones_by_due_date(self, eng, made, technician, fitter, machine):
        client, _ = eng
        owner_client, owner = technician
        later = added(client, made, owner, due_date=day(9))
        sooner = added(client, made, owner, due_date=day(-1), kind="correction")
        done = added(client, made, owner)
        assert mark_done(client, made, done).status_code == 200
        cancelled = added(client, made, owner)
        assert cancel(client, made, cancelled).status_code == 200
        added(client, made, fitter)   # another person's
        res = owner_client.get(MINE)
        assert res.status_code == 200
        page = res.get_json()
        assert page["total"] == 2
        assert [i["id"] for i in page["items"]] == [sooner["id"], later["id"]]
        first = page["items"][0]
        assert first == {
            "id": sooner["id"], "kind": "correction", "text": "Fit a sealed contact block", "due_date": day(-1),
            "overdue_days": 1, "can_mark_done": True, "can_add_photo": True,
            "improvement": {"id": made["id"], "serial": made["serial"], "title": made["title"],
                            "machine": {"id": machine["id"], "code": machine["code"], "name": machine["name"]}},
        }

    def test_no_team_record_gets_an_empty_list(self, role_client):
        res = role_client("it_admin").get(MINE)
        assert (res.status_code, res.get_json()) == (200, {"items": [], "total": 0})

    def test_an_operator_moved_off_the_unit_no_longer_sees_theirs(self, admin, eng, made, user_at_sites, site,
                                                                  unit, make_unit):
        client, _ = eng
        owner_client, owner = user_at_sites([(site, "maint_operator", [unit])])
        action = added(client, made, owner)
        assert [i["id"] for i in owner_client.get(MINE).get_json()["items"]] == [action["id"]]
        other_unit = make_unit(site)
        res = admin.put(f"{MASTERS}/people/{owner['id']}/sites/{site['id']}",
                        json={"role": "maint_operator", "all_units": False, "unit_ids": [other_unit["id"]]})
        assert res.status_code == 200, res.get_json()
        assert owner_client.get(MINE).get_json() == {"items": [], "total": 0}


# ---------------------------------------------------------------------------
# Owners
# ---------------------------------------------------------------------------

class TestOwners:

    def test_every_active_person_of_the_site_by_name(self, admin, eng, made, technician, fitter, user_at_sites,
                                                     site, other_site):
        client, person = eng
        _, storekeeper = user_at_sites([(site, "maint_storekeeper", "all")])
        _, inactive = user_at_sites([(site, "maint_technician", "all")])
        assert admin.put(f"{MASTERS}/people/{inactive['id']}", json={"active": False}).status_code == 200
        _, elsewhere = user_at_sites([(other_site, "maint_technician", "all")])
        res = client.get(OWNERS, query_string={"improvement_id": made["id"]})
        assert res.status_code == 200
        items = res.get_json()["items"]
        ids = [i["id"] for i in items]
        assert {person["id"], technician[1]["id"], fitter["id"], storekeeper["id"]} <= set(ids)
        assert inactive["id"] not in ids and elsewhere["id"] not in ids
        assert [i["name"] for i in items] == sorted(i["name"] for i in items)
        assert set(items[0]) == {"id", "name"}

    def test_refusals(self, eng, made, stranger, operator_here):
        client, _ = eng
        assert refusal(client.get(OWNERS)) == (400, "improvement_id", "improvement_id is required")
        assert stranger.get(OWNERS, query_string={"improvement_id": made["id"]}).status_code == 404
        assert operator_here.get(OWNERS, query_string={"improvement_id": made["id"]}).status_code == 403


# ---------------------------------------------------------------------------
# The countermeasure's lesson (S075 § 6.4, § 5.7)
# ---------------------------------------------------------------------------

class TestLesson:

    @staticmethod
    def write_lesson(client, machine, action):
        res = client.post("/api/procedures", json={"equipment_id": machine["id"], "title": "Keep the panel door shut",
                                                   "body": "Dust trips the contactor.", "action_id": action["id"]})
        assert res.status_code == 201, res.get_json()
        return res.get_json()

    def test_the_lesson_after_a_create(self, eng, made, machine):
        client, person = eng
        action = added(client, made, person, kind="lesson")
        assert (action["lesson"], action["can_write_lesson"]) == (None, True)
        lesson = self.write_lesson(client, machine, action)
        shown = the_action(get(client, made), action)
        assert shown["lesson"] == {"id": lesson["id"], "serial": lesson["serial"],
                                   "title": "Keep the panel door shut", "active": True}
        assert shown["can_write_lesson"] is False
        # The owner still marks it done (D8)
        assert shown["state"] == "open" and shown["can_mark_done"] is True

    def test_cancelled_another_kind_and_the_technician_owner(self, eng, made, technician):
        client, _ = eng
        tech_client, owner = technician
        lesson_kind = added(client, made, owner, kind="lesson")
        corrective = added(client, made, owner, kind="corrective")
        cancelled = added(client, made, owner, kind="lesson")
        assert cancel(client, made, cancelled).status_code == 200
        detail = get(client, made)
        assert [the_action(detail, a)["can_write_lesson"] for a in (lesson_kind, corrective, cancelled)] == [
            True, False, False]
        assert the_action(detail, corrective)["lesson"] is None
        assert the_action(get(tech_client, made), lesson_kind)["can_write_lesson"] is False

    def test_false_after_the_machine_moved_to_a_site_where_the_engineer_holds_no_key(
            self, admin, eng, made, machine, make_unit, other_site):
        """BR1-03: the improvement stays visible through its own unit, but the create would be 404."""
        client, person = eng
        action = added(client, made, person, kind="lesson")
        res = admin.put(f"/api/equipment/{machine['id']}", json={"unit_id": make_unit(site=other_site)["id"]})
        assert res.status_code == 200, res.get_json()
        assert the_action(get(client, made), action)["can_write_lesson"] is False
