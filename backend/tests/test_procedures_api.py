"""One-point lessons (S075 § 8.2), against the test DB.  Needs the dev MariaDB container.

Each test makes its own machines (make_equipment), so the kept worker database is the starting
state.  The engineers have real memberships (user_at_sites), since the site checks read
memberships, never the token.  "Another site" is a person with no membership at the machine's
site (404 by the machine's units); "a key missing here" is a person who is engineer at one site
and operator at the other (they read the other site's machine, but hold no key there: 403).
A countermeasure comes from S067's and S070's fixtures (an improvement on a ticket of the machine).
"""

import re

import pytest

from tests.documents_helpers import JPEG, refusal, scrap, uploaded_to
from tests.test_improvements_api import (  # noqa: F401  (fixtures used by name)
    IMPROVEMENTS, eng, other_site, restored_ticket, site, started,
)
from tests.ticket_helpers import now_ist

LESSONS = "/api/procedures"
SERIAL = re.compile(r"^OPL-(\d{3,})$")
TAMIL_TITLE = "பேனல் கதவை மூடி வை"
TAMIL_BODY = "தூசி கான்டாக்டரை நிறுத்தும்.\nKeep the panel door shut."


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def stranger(user_at_sites, other_site):
    """An engineer of another site: the machine is outside their units (404)."""
    return user_at_sites([(other_site, "maint_engineer", "all")])[0]


@pytest.fixture
def operator(user_at_sites, site):
    return user_at_sites([(site, "maint_operator", "all")])[0]


@pytest.fixture
def operator_elsewhere(user_at_sites, other_site):
    """An operator of another site's units: reads class lessons, never this site's machine lessons."""
    return user_at_sites([(other_site, "maint_operator", "all")])[0]


@pytest.fixture
def improvement(eng, restored_ticket):
    """An improvement on a ticket of the machine, led by the engineer."""
    client, person = eng
    return started(client, restored_ticket(), person)


def body(machine, **overrides):
    return {"equipment_id": machine["id"], "title": "Keep the panel door shut",
            "body": "Dust trips the contactor.", **overrides}


def create(client, machine, **overrides):
    return client.post(LESSONS, json=body(machine, **overrides))


def created(client, machine, **overrides):
    res = create(client, machine, **overrides)
    assert res.status_code == 201, res.get_json()
    return res.get_json()


def change(client, lesson, **fields):
    return client.put(f"{LESSONS}/{lesson['id']}", json=fields)


def changed(client, lesson, **fields):
    res = change(client, lesson, **fields)
    assert res.status_code == 200, res.get_json()
    return res.get_json()


def detail(client, lesson):
    res = client.get(f"{LESSONS}/{lesson['id']}")
    assert res.status_code == 200, res.get_json()
    return res.get_json()


def listing(client, node):
    res = client.get(LESSONS, query_string={"equipment_id": node["id"]})
    assert res.status_code == 200, res.get_json()
    return res.get_json()


def ids(items):
    return [item["id"] for item in items]


def number(serial):
    return int(SERIAL.match(serial).group(1))


def add_action(client, improvement, owner, kind="lesson"):
    res = client.post(f"{IMPROVEMENTS}/{improvement['id']}/actions", json={
        "kind": kind, "text": "Teach the panel rule", "owner_id": owner["id"],
        "due_date": now_ist().date().isoformat()})
    assert res.status_code == 201, res.get_json()
    return res.get_json()["actions"][-1]


def action_post(client, improvement, action, suffix, payload):
    res = client.post(f"{IMPROVEMENTS}/{improvement['id']}/actions/{action['id']}/{suffix}", json=payload)
    assert res.status_code == 200, res.get_json()


def photo(client, lesson, title="Dusty contactor"):
    return uploaded_to(client, f"{LESSONS}/{lesson['id']}/documents", kind="photo", title=title, data=JPEG,
                       filename="IMG_1.jpg")


def site_code(db_rows, site):
    return db_rows("SELECT code FROM sites WHERE id = %s", (site["id"],))[0]["code"]


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

class TestCreate:

    def test_an_engineer_writes_a_lesson_on_a_machine_of_the_site(self, eng, machine):
        client, person = eng
        lesson = created(client, machine)
        assert SERIAL.match(lesson["serial"])
        assert (lesson["kind"], lesson["title"], lesson["body"], lesson["active"]) == (
            "one_point_lesson", "Keep the panel door shut", "Dust trips the contactor.", True)
        assert (lesson["for_class"], lesson["class"], lesson["source"], lesson["documents"]) == (False, None, None, [])
        assert lesson["machine"] == {"id": machine["id"], "code": machine["code"], "name": machine["name"]}
        assert lesson["created_by_name"] == person["name"]
        assert (lesson["updated_at"], lesson["updated_by_name"]) == (None, None)
        assert (lesson["can_edit"], lesson["can_change_class"]) == (True, True)

    def test_for_the_class_stores_the_machines_class(self, eng, machine, db_rows):
        client, _ = eng
        lesson = created(client, machine, for_class=True)
        class_id = db_rows("SELECT class_id FROM equipment WHERE id = %s", (machine["id"],))[0]["class_id"]
        assert lesson["for_class"] is True and lesson["class"]["id"] == class_id
        assert db_rows("SELECT class_id FROM procedures WHERE id = %s", (lesson["id"],))[0]["class_id"] == class_id

    def test_a_tamil_title_and_body_are_stored_and_answered_unchanged(self, eng, machine, db_rows):
        client, _ = eng
        lesson = created(client, machine, title=TAMIL_TITLE, body=TAMIL_BODY)
        assert (lesson["title"], lesson["body"]) == (TAMIL_TITLE, TAMIL_BODY.strip())
        assert list(db_rows("SELECT title, body FROM procedures WHERE id = %s", (lesson["id"],))) == [
            {"title": TAMIL_TITLE, "body": TAMIL_BODY.strip()}]

    @pytest.mark.parametrize("role", ["maint_operator", "maint_supervisor", "maint_technician", "it_admin",
                                      "maint_storekeeper"])
    def test_other_roles_are_403(self, role_client, machine, role):
        assert create(role_client(role), machine).status_code == 403

    def test_an_engineer_of_another_site_is_404(self, stranger, machine):
        assert create(stranger, machine).status_code == 404

    def test_an_operator_there_without_the_key_there_is_403(self, user_at_sites, site, other_site, make_unit,
                                                            make_equipment, db_rows):
        client, _ = user_at_sites([(site, "maint_engineer", "all"), (other_site, "maint_operator", "all")])
        there = make_equipment(unit=make_unit(site=other_site))
        assert refusal(create(client, there)) == (403, None, f"You can't do this at {site_code(db_rows, other_site)}")

    def test_a_scrapped_machine_takes_a_lesson(self, eng, admin, make_equipment, unit):
        client, _ = eng
        old = make_equipment(unit=unit)
        scrap(admin, old)
        assert created(client, old)["machine"]["id"] == old["id"]

    def test_two_creates_give_consecutive_serials_and_a_refused_one_leaves_no_gap(self, eng, machine):
        client, _ = eng
        first = created(client, machine)
        assert create(client, machine, title="").status_code == 400
        assert create(client, machine, action_id=999999999).status_code == 400
        assert number(created(client, machine)["serial"]) == number(first["serial"]) + 1

    def test_the_field_messages(self, eng, machine):
        client, _ = eng
        assert refusal(create(client, machine, title="x" * 81)) == (400, "title", "Title: up to 80 characters")
        assert refusal(create(client, machine, body="")) == (400, "body", "Enter the lesson text")
        assert refusal(create(client, machine, for_class="yes")) == (
            400, "for_class", "For the class must be true or false")
        assert refusal(client.post(LESSONS, json={"title": "x", "body": "y"})) == (
            400, "equipment_id", "Choose the machine")
        assert create(client, {"id": 999999999}).status_code == 404

    def test_the_database_down_is_503(self, role_client, db_down):
        assert role_client("maint_engineer").post(LESSONS, json={"equipment_id": 1, "title": "x",
                                                                 "body": "y"}).status_code == 503


# ---------------------------------------------------------------------------
# Create with a countermeasure (§ 5.3)
# ---------------------------------------------------------------------------

class TestCreateFromACountermeasure:

    def test_an_open_lesson_countermeasure_links(self, eng, machine, improvement, db_rows):
        client, person = eng
        action = add_action(client, improvement, person)
        lesson = created(client, machine, action_id=action["id"])
        assert lesson["source"] == {"improvement": {"id": improvement["id"], "serial": improvement["serial"],
                                                    "title": improvement["title"]}, "action_id": action["id"]}
        assert db_rows("SELECT action_id FROM procedures WHERE id = %s", (lesson["id"],))[0]["action_id"] == action["id"]

    def test_a_done_one_links(self, eng, machine, improvement):
        client, person = eng
        action = add_action(client, improvement, person)
        action_post(client, improvement, action, "done", {"done_text": "Taught at the press"})
        assert created(client, machine, action_id=action["id"])["source"]["action_id"] == action["id"]

    def test_another_kind_is_409(self, eng, machine, improvement):
        client, person = eng
        action = add_action(client, improvement, person, kind="corrective")
        assert refusal(create(client, machine, action_id=action["id"])) == (
            409, "action_id", "Only a countermeasure of kind Lesson links a lesson")

    def test_a_cancelled_one_is_409(self, eng, machine, improvement):
        client, person = eng
        action = add_action(client, improvement, person)
        action_post(client, improvement, action, "cancel", {"reason": "Not needed"})
        assert refusal(create(client, machine, action_id=action["id"])) == (
            409, "action_id", "This countermeasure was cancelled")

    def test_one_of_an_improvement_the_user_cannot_open_is_400(self, eng, improvement, user_at_sites, other_site,
                                                                make_unit, make_equipment):
        client, person = eng
        action = add_action(client, improvement, person)
        there, _ = user_at_sites([(other_site, "maint_engineer", "all")])
        their_machine = make_equipment(unit=make_unit(site=other_site))
        assert refusal(create(there, their_machine, action_id=action["id"])) == (
            400, "action_id", "Choose a countermeasure")

    def test_on_another_machine_than_the_improvements_is_400(self, eng, machine, improvement, make_equipment, unit):
        client, person = eng
        action = add_action(client, improvement, person)
        other = make_equipment(unit=unit)
        assert refusal(create(client, other, action_id=action["id"])) == (
            400, "equipment_id", f"A lesson for this countermeasure goes on {machine['code']}, the improvement's machine")

    def test_a_second_lesson_for_it_is_409_naming_the_first(self, eng, machine, improvement):
        client, person = eng
        action = add_action(client, improvement, person)
        first = created(client, machine, action_id=action["id"])
        assert refusal(create(client, machine, action_id=action["id"])) == (
            409, "action_id", f"This countermeasure already has its lesson, {first['serial']}")

    def test_a_closed_improvements_done_countermeasure_links_and_the_improvement_is_untouched(
            self, eng, machine, improvement, db_rows):
        client, person = eng
        action = add_action(client, improvement, person)
        action_post(client, improvement, action, "done", {"done_text": "Taught at the press"})
        db_rows("UPDATE improvements SET state = 'closed_effective', watch_from = NOW(), closed_at = NOW(),"
                " closed_by = 'kla' WHERE id = %s", (improvement["id"],))

        def improvement_now():
            return (db_rows("SELECT state, updated_at FROM improvements WHERE id = %s", (improvement["id"],)),
                    db_rows("SELECT COUNT(*) AS n FROM improvement_events WHERE improvement_id = %s",
                            (improvement["id"],)),
                    db_rows("SELECT state, updated_at FROM improvement_actions WHERE id = %s", (action["id"],)))
        before = improvement_now()
        created(client, machine, action_id=action["id"])
        assert improvement_now() == before


# ---------------------------------------------------------------------------
# Change (§ 5.2–§ 5.5)
# ---------------------------------------------------------------------------

class TestChange:

    def test_each_field(self, eng, machine):
        client, person = eng
        lesson = created(client, machine)
        out = changed(client, lesson, title="  Shut  the\ndoor ", body="New text\nline two")
        assert (out["title"], out["body"]) == ("Shut the door", "New text\nline two")
        assert out["updated_at"] and out["updated_by_name"] == person["name"]

    def test_no_change_writes_nothing(self, eng, machine, db_rows):
        client, _ = eng
        lesson = created(client, machine)
        out = changed(client, lesson, title=lesson["title"], body=lesson["body"], active=True, for_class=False)
        assert out["updated_at"] is None
        assert db_rows("SELECT updated_at FROM procedures WHERE id = %s", (lesson["id"],))[0]["updated_at"] is None

    def test_the_tick_on_and_off(self, eng, machine, db_rows):
        client, _ = eng
        lesson = created(client, machine)
        on = changed(client, lesson, for_class=True)
        stored = db_rows("SELECT class_id FROM procedures WHERE id = %s", (lesson["id"],))[0]["class_id"]
        assert on["for_class"] is True and stored is not None and on["class"]["id"] == stored
        off = changed(client, lesson, for_class=False)
        assert off["for_class"] is False and off["class"] is None
        assert db_rows("SELECT class_id FROM procedures WHERE id = %s", (lesson["id"],))[0]["class_id"] is None

    def test_a_class_lesson_is_changed_from_another_site_but_not_unticked(self, eng, stranger, machine, db_rows,
                                                                          site):
        client, _ = eng
        lesson = created(client, machine, for_class=True)
        out = changed(stranger, lesson, title="Shut the door", active=False)
        assert (out["title"], out["active"], out["machine"]) == ("Shut the door", False, None)
        assert (out["can_edit"], out["can_change_class"]) == (True, False)
        assert refusal(change(stranger, lesson, for_class=False)) == (
            403, None, f"You can't do this at {site_code(db_rows, site)}")

    def test_a_machine_lesson_from_another_site_is_404(self, eng, stranger, machine):
        client, _ = eng
        lesson = created(client, machine)
        assert change(stranger, lesson, title="x").status_code == 404
        assert change(client, {"id": 999999999}, title="x").status_code == 404

    def test_retire_and_bring_back(self, eng, machine, operator):
        client, _ = eng
        lesson = created(client, machine)
        assert changed(client, lesson, active=False)["active"] is False
        assert ids(listing(operator, machine)["items"]) == []
        assert detail(operator, lesson)["active"] is False   # the page stays open
        assert changed(client, lesson, active=True)["active"] is True
        assert ids(listing(operator, machine)["items"]) == [lesson["id"]]

    def test_a_countermeasure_set_on_an_unlinked_lesson_and_kept_once_set(self, eng, machine, improvement):
        client, person = eng
        action = add_action(client, improvement, person)
        lesson = created(client, machine)
        assert changed(client, lesson, action_id=action["id"])["source"]["action_id"] == action["id"]
        assert changed(client, lesson, action_id=action["id"])["source"]["action_id"] == action["id"]
        other = add_action(client, improvement, person)
        kept = (409, "action_id", "A lesson keeps the countermeasure it was written for")
        assert refusal(change(client, lesson, action_id=other["id"])) == kept
        assert refusal(change(client, lesson, action_id=None)) == kept

    def test_the_link_checks_run_on_a_change_too(self, eng, machine, improvement):
        client, person = eng
        corrective = add_action(client, improvement, person, kind="corrective")
        assert change(client, created(client, machine), action_id=corrective["id"]).status_code == 409

    def test_other_roles_are_403(self, eng, machine, role_client):
        client, _ = eng
        lesson = created(client, machine)
        assert change(role_client("maint_technician"), lesson, title="x").status_code == 403


# ---------------------------------------------------------------------------
# A machine's lessons (§ 6.2)
# ---------------------------------------------------------------------------

class TestList:

    def test_its_own_and_its_class_newest_first_not_a_part_or_the_parent(self, eng, make_equipment, make_class,
                                                                         unit):
        client, _ = eng
        cls = make_class()
        press, sister = make_equipment(unit=unit, cls=cls), make_equipment(unit=unit, cls=cls)
        part = make_equipment(parent=press)
        own = created(client, press)
        for_class = created(client, sister, for_class=True)
        sisters_own = created(client, sister)
        parts = created(client, part)
        page = listing(client, press)
        assert ids(page["items"]) == [for_class["id"], own["id"]]
        assert page["total"] == 2 and page["retired"] == [] and page["can_add"] is True
        own_item = page["items"][1]
        assert (own_item["own"], own_item["for_class"], own_item["class"], own_item["active"], own_item["cover"]) == (
            True, False, None, True, None)
        class_item = page["items"][0]
        assert class_item["own"] is False and class_item["class"]["id"] == cls["id"]
        assert class_item["class"]["code"] == cls["code"] and class_item["class"]["name"] == cls["name"]
        assert sisters_own["id"] not in ids(page["items"]) and parts["id"] not in ids(page["items"])
        assert ids(listing(client, part)["items"]) == [parts["id"]]

    def test_retired_lessons_only_in_retired_and_only_for_writers(self, eng, machine, operator):
        client, _ = eng
        kept, retired = created(client, machine), created(client, machine)
        changed(client, retired, active=False)
        page = listing(client, machine)
        assert (ids(page["items"]), ids(page["retired"]), page["total"]) == ([kept["id"]], [retired["id"]], 1)
        assert page["retired"][0]["active"] is False
        theirs = listing(operator, machine)
        assert (ids(theirs["items"]), theirs["retired"], theirs["can_add"]) == ([kept["id"]], [], False)

    def test_the_cover_is_the_oldest_photo_not_removed(self, eng, machine):
        client, _ = eng
        lesson = created(client, machine)
        uploaded_to(client, f"{LESSONS}/{lesson['id']}/documents")   # a PDF is never the cover
        first, second = photo(client, lesson), photo(client, lesson, "Clean contactor")
        cover = listing(client, machine)["items"][0]["cover"]
        assert cover == {"doc_id": first["id"], "has_thumb": True}
        assert client.delete(f"{LESSONS}/{lesson['id']}/documents/{first['id']}").status_code == 204
        assert listing(client, machine)["items"][0]["cover"]["doc_id"] == second["id"]

    def test_a_node_outside_the_units_is_404_and_the_machine_is_required(self, eng, stranger, machine):
        client, _ = eng
        assert stranger.get(LESSONS, query_string={"equipment_id": machine["id"]}).status_code == 404
        assert refusal(client.get(LESSONS)) == (400, "equipment_id", "equipment_id is required")
        assert client.get(f"{LESSONS}/").status_code == 400   # strict_slashes=False: no 308

    def test_an_operator_of_another_site_sees_a_class_lesson_on_their_machine(self, eng, machine, make_equipment,
                                                                              make_unit, other_site,
                                                                              operator_elsewhere, db_rows):
        client, _ = eng
        class_id = db_rows("SELECT class_id FROM equipment WHERE id = %s", (machine["id"],))[0]["class_id"]
        theirs = make_equipment(unit=make_unit(site=other_site), cls={"id": class_id})
        lesson = created(client, machine, for_class=True)
        assert ids(listing(operator_elsewhere, theirs)["items"]) == [lesson["id"]]


# ---------------------------------------------------------------------------
# One lesson (§ 6.3)
# ---------------------------------------------------------------------------

class TestDetail:

    def test_documents_oldest_first(self, eng, machine):
        client, _ = eng
        lesson = created(client, machine)
        first, second = photo(client, lesson), photo(client, lesson, "Clean contactor")
        assert ids(detail(client, lesson)["documents"]) == [first["id"], second["id"]]
        assert detail(client, lesson)["documents"][0] == {"id": first["id"], "kind": "photo",
                                                          "title": "Dusty contactor", "has_thumb": True}

    def test_a_class_lesson_by_another_sites_operator_and_a_machine_lesson_not(self, eng, machine,
                                                                               operator_elsewhere):
        client, _ = eng
        for_class = created(client, machine, for_class=True)
        seen = detail(operator_elsewhere, for_class)
        assert seen["machine"] is None and seen["class"] is not None
        assert (seen["can_edit"], seen["can_change_class"]) == (False, False)
        assert operator_elsewhere.get(f"{LESSONS}/{created(client, machine)['id']}").status_code == 404

    def test_the_source_for_a_reader_of_the_improvement_only(self, eng, machine, improvement, operator,
                                                             user_at_sites, site):
        client, person = eng
        action = add_action(client, improvement, person)
        lesson = created(client, machine, action_id=action["id"])
        assert detail(operator, lesson)["source"]["improvement"]["serial"] == improvement["serial"]
        storekeeper, _ = user_at_sites([(site, "maint_storekeeper", "all")])
        assert detail(storekeeper, lesson)["source"] is None

    def test_the_flags_for_the_engineer_here_and_elsewhere(self, eng, stranger, machine):
        client, _ = eng
        machine_lesson, class_lesson = created(client, machine), created(client, machine, for_class=True)
        assert (detail(client, machine_lesson)["can_edit"], detail(client, machine_lesson)["can_change_class"]) == (
            True, True)
        theirs = detail(stranger, class_lesson)
        assert (theirs["can_edit"], theirs["can_change_class"]) == (True, False)

    def test_a_missing_lesson_is_404(self, eng):
        client, _ = eng
        assert client.get(f"{LESSONS}/999999999").status_code == 404
