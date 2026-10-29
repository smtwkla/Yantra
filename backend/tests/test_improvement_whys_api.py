"""The why-why chain and the root cause (S069 § 8.2), against the test DB.  Needs the dev MariaDB
container.

Each test starts its own improvement on its own ticket (S067's fixtures, imported from
test_improvements_api), so the kept worker database is the starting state.  "Another site" and
"a key missing here" as S067 § 8.2: a person with no membership at the improvement's site (404),
and one who is operator here and engineer at another site (403).
"""

import pytest

import improvements_core
from tests.test_improvements_api import (  # noqa: F401  (fixtures used by name)
    IMPROVEMENTS, eng, get, other_site, restored_ticket, site, started,
)
from tests.ticket_helpers import refusal

CAUSES = "/api/masters/failure-causes"


@pytest.fixture
def made(eng, restored_ticket):
    client, person = eng
    return started(client, restored_ticket(), person)


@pytest.fixture
def operator(user_at_sites, site):
    return user_at_sites([(site, "maint_operator", "all")])[0]


@pytest.fixture
def stranger(user_at_sites, other_site):
    """An engineer of another site: the predicate hides the improvement (404)."""
    return user_at_sites([(other_site, "maint_engineer", "all")])[0]


@pytest.fixture
def operator_here(user_at_sites, site, other_site):
    """Operator here, engineer elsewhere: the predicate passes, the key at the site does not (403)."""
    return user_at_sites([(site, "maint_operator", "all"), (other_site, "maint_engineer", "all")])[0]


@pytest.fixture
def cause_id(db_rows):
    def find(code):
        return db_rows("SELECT id FROM failure_causes WHERE code = %s", (code,))[0]["id"]
    return find


@pytest.fixture
def new_cause(admin, uniq):
    """A cause of its own (so deactivating it touches no seed row) -> its row."""
    def make():
        res = admin.post(CAUSES, json={"code": uniq.failure_code(), "label": uniq.failure_label(),
                                       "cause_group": "management"})
        assert res.status_code == 201, res.get_json()
        return res.get_json()
    return make


def why_url(improvement, why=None):
    base = f"{IMPROVEMENTS}/{improvement['id']}/whys"
    return base if why is None else f"{base}/{why['id']}"


def add_why(client, improvement, question="Why?", answer="Because", **extra):
    return client.post(why_url(improvement), json={"question": question, "answer": answer, **extra})


def chain(client, improvement, n):
    """n whys A, B, C, … -> the detail's whys."""
    whys = None
    for letter in "ABCDEFGHIJ"[:n]:
        res = add_why(client, improvement, f"Why {letter}?", f"Because {letter}")
        assert res.status_code == 201, res.get_json()
        whys = res.get_json()["whys"]
    return whys


def order(detail):
    return [(w["position"], w["question"]) for w in detail["whys"]]


def put_root(client, improvement, **fields):
    return client.put(f"{IMPROVEMENTS}/{improvement['id']}/root-cause", json=fields)


# ---------------------------------------------------------------------------
# Add why
# ---------------------------------------------------------------------------

class TestAddWhy:

    def test_three_whys_get_positions_one_two_three(self, eng, made):
        client, person = eng
        whys = chain(client, made, 3)
        assert [(w["position"], w["question"], w["answer"]) for w in whys] == [
            (1, "Why A?", "Because A"), (2, "Why B?", "Because B"), (3, "Why C?", "Because C")]
        assert all(w["created_by_name"] == person["name"] and w["evidence"] is None for w in whys)
        assert all(w["updated_at"] is None and w["updated_by_name"] is None for w in whys)

    def test_evidence_kept_trimmed(self, eng, made):
        client, _ = eng
        res = add_why(client, made, evidence="  Photo of the contacts  ")
        assert res.get_json()["whys"][0]["evidence"] == "Photo of the contacts"

    def test_who_may_add(self, operator, operator_here, stranger, eng, made):
        assert add_why(operator, made).status_code == 403
        assert add_why(operator_here, made).status_code == 403
        assert add_why(stranger, made).status_code == 404
        client, _ = eng
        assert add_why(client, {"id": 999999999}).status_code == 404

    def test_the_21st_why_is_409(self, eng, made, db_rows):
        client, _ = eng
        for position in range(1, 21):
            db_rows("INSERT INTO improvement_whys (improvement_id, position, question, answer, created_by)"
                    " VALUES (%s, %s, 'Why?', 'Because', 'kla')", (made["id"], position))
        assert refusal(add_why(client, made)) == (409, None, "An analysis holds up to 20 whys. Change a why instead.")

    def test_bounds(self, eng, made):
        client, _ = eng
        assert refusal(add_why(client, made, question="x" * 301)) == (400, "question", "Question: up to 300 characters")
        assert refusal(add_why(client, made, answer="  ")) == (400, "answer", "Enter the answer")
        assert refusal(add_why(client, made, evidence="x" * 501)) == (400, "evidence", "Evidence: up to 500 characters")

    def test_a_closed_improvement_is_409(self, monkeypatch, eng, made):
        """Every improvement is open until R05.4: the check is proved with no open state."""
        monkeypatch.setattr(improvements_core, "IMPROVEMENT_OPEN_STATES", ())
        client, _ = eng
        assert refusal(add_why(client, made)) == (409, None, "This improvement is closed")

    def test_the_database_down_is_503(self, eng, made, db_down):
        client, _ = eng
        assert add_why(client, made).status_code == 503


# ---------------------------------------------------------------------------
# Edit why
# ---------------------------------------------------------------------------

class TestEditWhy:

    def test_the_text_of_why_two(self, eng, made):
        client, person = eng
        whys = chain(client, made, 3)
        res = client.put(why_url(made, whys[1]), json={"answer": " Dust on the faces ", "evidence": "Photo"})
        assert res.status_code == 200, res.get_json()
        after = res.get_json()["whys"]
        assert (after[1]["answer"], after[1]["evidence"]) == ("Dust on the faces", "Photo")
        assert after[1]["updated_at"] is not None and after[1]["updated_by_name"] == person["name"]
        assert [after[0], after[2]] == [whys[0], whys[2]]

    def test_no_change_writes_nothing(self, eng, made, db_rows):
        client, _ = eng
        why = chain(client, made, 2)[1]
        before = db_rows("SELECT * FROM improvement_whys WHERE improvement_id = %s", (made["id"],))
        res = client.put(why_url(made, why), json={"question": why["question"], "answer": why["answer"],
                                                   "evidence": "", "position": 2})
        assert res.status_code == 200
        assert db_rows("SELECT * FROM improvement_whys WHERE improvement_id = %s", (made["id"],)) == before

    def test_move_three_to_one(self, eng, made, db_rows):
        client, _ = eng
        whys = chain(client, made, 3)
        res = client.put(why_url(made, whys[2]), json={"position": 1})
        assert res.status_code == 200
        assert order(res.get_json()) == [(1, "Why C?"), (2, "Why A?"), (3, "Why B?")]
        stamped = {r["id"]: r["updated_at"] is not None
                   for r in db_rows("SELECT id, updated_at FROM improvement_whys WHERE improvement_id = %s",
                                    (made["id"],))}
        assert stamped == {whys[0]["id"]: False, whys[1]["id"]: False, whys[2]["id"]: True}

    @pytest.mark.parametrize("position", [0, 4])
    def test_a_place_outside_the_chain_is_400(self, eng, made, position):
        client, _ = eng
        whys = chain(client, made, 3)
        assert refusal(client.put(why_url(made, whys[0]), json={"position": position})) == (
            400, "position", "Choose a place from 1 to 3")

    def test_null_text_is_400(self, eng, made):
        client, _ = eng
        why = chain(client, made, 1)[0]
        assert refusal(client.put(why_url(made, why), json={"question": None})) == (
            400, "question", "Enter the question")

    def test_a_why_of_another_improvement_is_404(self, eng, made, restored_ticket):
        client, person = eng
        other = started(client, restored_ticket(), person)
        why = chain(client, other, 1)[0]
        assert client.put(why_url(made, why), json={"answer": "x"}).status_code == 404
        assert client.put(why_url(made, {"id": 999999999}), json={"answer": "x"}).status_code == 404

    def test_who_may_edit(self, operator_here, stranger, eng, made):
        client, _ = eng
        why = chain(client, made, 1)[0]
        assert operator_here.put(why_url(made, why), json={"answer": "x"}).status_code == 403
        assert stranger.put(why_url(made, why), json={"answer": "x"}).status_code == 404


# ---------------------------------------------------------------------------
# Remove why
# ---------------------------------------------------------------------------

class TestRemoveWhy:

    def test_why_two_of_three(self, eng, made):
        client, _ = eng
        whys = chain(client, made, 3)
        res = client.delete(why_url(made, whys[1]))
        assert res.status_code == 200
        assert order(res.get_json()) == [(1, "Why A?"), (2, "Why C?")]

    def test_the_last_why(self, eng, made):
        client, _ = eng
        whys = chain(client, made, 2)
        assert order(client.delete(why_url(made, whys[1])).get_json()) == [(1, "Why A?")]
        assert client.delete(why_url(made, whys[0])).get_json()["whys"] == []

    def test_a_why_of_another_improvement_is_404(self, eng, made, restored_ticket):
        client, person = eng
        other = started(client, restored_ticket(), person)
        why = chain(client, other, 1)[0]
        assert client.delete(why_url(made, why)).status_code == 404
        assert len(get(client, other)["whys"]) == 1

    def test_the_operator_is_403(self, operator, eng, made):
        client, _ = eng
        why = chain(client, made, 1)[0]
        assert operator.delete(why_url(made, why)).status_code == 403


# ---------------------------------------------------------------------------
# Root cause
# ---------------------------------------------------------------------------

class TestRootCause:

    def test_set_with_an_active_cause(self, eng, made, cause_id, db_rows):
        client, _ = eng
        tickets_before = db_rows("SELECT * FROM tickets t JOIN improvement_tickets it ON it.ticket_id = t.id"
                                 " WHERE it.improvement_id = %s", (made["id"],))
        res = put_root(client, made, root_cause=" The presses have no PM plan ", root_cause_id=cause_id("4.2"))
        assert res.status_code == 200, res.get_json()
        shown = res.get_json()
        assert shown["root_cause"]["text"] == "The presses have no PM plan"
        assert {k: shown["root_cause"]["cause"][k] for k in ("id", "code", "cause_group", "active")} == {
            "id": cause_id("4.2"), "code": "4.2", "cause_group": "management", "active": True}
        assert shown["contributing_causes"] is None
        assert db_rows("SELECT * FROM tickets t JOIN improvement_tickets it ON it.ticket_id = t.id"
                       " WHERE it.improvement_id = %s", (made["id"],)) == tickets_before

    def test_a_new_improvement_has_none(self, eng, made):
        assert (made["root_cause"], made["contributing_causes"], made["whys"]) == (None, None, [])

    def test_missing_text_or_cause_is_400(self, eng, made, cause_id):
        client, _ = eng
        assert refusal(put_root(client, made, root_cause_id=cause_id("4.2"))) == (
            400, "root_cause", "Enter the root cause")
        assert refusal(put_root(client, made, root_cause="No PM plan")) == (400, "root_cause_id", "Choose the cause")

    def test_an_inactive_cause_newly_chosen_is_400(self, admin, eng, made, new_cause):
        client, _ = eng
        cause = new_cause()
        assert admin.put(f"{CAUSES}/{cause['id']}", json={"active": False}).status_code == 200
        assert refusal(put_root(client, made, root_cause="No PM plan", root_cause_id=cause["id"])) == (
            400, "root_cause_id", "Choose an active cause from the list")
        assert refusal(put_root(client, made, root_cause="No PM plan", root_cause_id=999999999)) == (
            400, "root_cause_id", "Choose an active cause from the list")

    def test_a_cause_deactivated_later_is_kept_on_a_text_change(self, admin, eng, made, new_cause):
        client, _ = eng
        cause = new_cause()
        assert put_root(client, made, root_cause="No PM plan", root_cause_id=cause["id"]).status_code == 200
        assert admin.put(f"{CAUSES}/{cause['id']}", json={"active": False}).status_code == 200
        res = put_root(client, made, root_cause="No PM plan for the presses", root_cause_id=cause["id"])
        assert res.status_code == 200, res.get_json()
        shown = res.get_json()["root_cause"]
        assert (shown["text"], shown["cause"]["id"], shown["cause"]["active"]) == (
            "No PM plan for the presses", cause["id"], False)

    def test_contributing_causes_set_then_cleared(self, eng, made, cause_id):
        client, _ = eng
        base = {"root_cause": "No PM plan", "root_cause_id": cause_id("4.2")}
        res = put_root(client, made, **base, contributing_causes=" Dusty shop floor ")
        assert res.get_json()["contributing_causes"] == "Dusty shop floor"
        assert put_root(client, made, **base).get_json()["contributing_causes"] == "Dusty shop floor"
        assert put_root(client, made, **base, contributing_causes="").get_json()["contributing_causes"] is None

    def test_no_change_writes_nothing(self, eng, made, cause_id, db_rows):
        client, _ = eng
        base = {"root_cause": "No PM plan", "root_cause_id": cause_id("4.2")}
        assert put_root(client, made, **base).status_code == 200
        before = db_rows("SELECT * FROM improvements WHERE id = %s", (made["id"],))
        assert put_root(client, made, **base).status_code == 200
        assert db_rows("SELECT * FROM improvements WHERE id = %s", (made["id"],)) == before

    def test_who_may_set_it(self, operator, stranger, made, cause_id):
        base = {"root_cause": "No PM plan", "root_cause_id": cause_id("4.2")}
        assert put_root(operator, made, **base).status_code == 403
        assert put_root(stranger, made, **base).status_code == 404

    def test_the_improvement_edit_ignores_the_root_cause(self, eng, made, cause_id):
        client, _ = eng
        res = client.put(f"{IMPROVEMENTS}/{made['id']}", json={"root_cause": "x", "root_cause_id": cause_id("4.2")})
        assert res.status_code == 200 and res.get_json()["root_cause"] is None


# ---------------------------------------------------------------------------
# Detail and list
# ---------------------------------------------------------------------------

class TestDetail:

    def test_an_operator_of_the_unit_reads_the_analysis(self, operator, eng, made, cause_id):
        client, _ = eng
        whys = chain(client, made, 2)
        client.put(why_url(made, whys[1]), json={"position": 1})
        put_root(client, made, root_cause="No PM plan", root_cause_id=cause_id("4.2"), contributing_causes="Dust")
        shown = get(operator, made)
        assert order(shown) == [(1, "Why B?"), (2, "Why A?")]
        assert (shown["root_cause"]["text"], shown["root_cause"]["cause"]["code"], shown["contributing_causes"]) == (
            "No PM plan", "4.2", "Dust")

    def test_the_list_item_gains_no_field(self, eng, made, cause_id):
        client, _ = eng
        put_root(client, made, root_cause="No PM plan", root_cause_id=cause_id("4.2"))
        item = next(x for x in client.get(IMPROVEMENTS).get_json()["items"] if x["id"] == made["id"])
        assert not {"root_cause", "contributing_causes", "whys"} & set(item)
