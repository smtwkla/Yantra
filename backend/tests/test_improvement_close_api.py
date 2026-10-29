"""The states, the watch, the verified close and the drop (S072 § 8.2), against the test DB.  Needs the dev
MariaDB container.

Each test starts its own improvement on its own ticket (S067's fixtures), so the kept worker database is the
starting state.  The watch's past is made by the API where it can: the ticket's time is moved back (db_rows),
and S070 lets a countermeasure's done_at go back to it; the watch is then shortened to 30 days by S067's PUT.
"Another site" and "a key missing here" as S067 § 8.2.
"""

from datetime import datetime, timedelta

import pytest

import improvements
from tests.documents_helpers import JPEG, upload_to
from tests.test_improvements_api import (  # noqa: F401  (fixtures used by name)
    IMPROVEMENTS, add, eng, get, no_cause, number, other_site, remove, restored_ticket, site, start, started,
    ticket_detail,
)
from tests.ticket_helpers import now_ist, refusal
from tickets_core import ticket_times

CLOSED = "This improvement is closed"
VERIFY_NOT_YET = "Verify once every countermeasure is done and the watch has ended"
DAY = timedelta(days=1)


# ---------------------------------------------------------------------------
# Fixtures and helpers (the timeline tests import them)
# ---------------------------------------------------------------------------

@pytest.fixture
def modes(db_rows):
    """Two symptoms (failure modes) of the seed list."""
    return [r["id"] for r in db_rows("SELECT id FROM failure_modes WHERE active = 1 ORDER BY id LIMIT 2")]


@pytest.fixture
def aged(eng, restored_ticket, db_rows, modes):
    """aged(days=40) -> (improvement, ticket): an improvement led by the engineer on a critical ticket that
    happened ``days`` ago with the first symptom."""
    client, person = eng

    def make(days=40, ticket=None):
        ticket = ticket or restored_ticket()
        db_rows("UPDATE tickets SET occurred_at = %s, failure_mode_id = %s WHERE id = %s",
                (minute(now_ist() - days * DAY), modes[0], ticket["id"]))
        return started(client, ticket, person), ticket
    return make


@pytest.fixture
def manager(user_at_sites, site):
    return user_at_sites([(site, "maint_manager", "all")])


@pytest.fixture
def operator_at_site(user_at_sites, site):
    return user_at_sites([(site, "maint_operator", "all")])


@pytest.fixture
def operator_here(user_at_sites, site, other_site):
    """Operator here, engineer elsewhere: the predicate passes, the key at the site does not (403)."""
    return user_at_sites([(site, "maint_operator", "all"), (other_site, "maint_engineer", "all")])[0]


@pytest.fixture
def stranger(user_at_sites, other_site):
    return user_at_sites([(other_site, "maint_engineer", "all")])[0]


def minute(dt):
    return dt.replace(second=0, microsecond=0)


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S+05:30")


def url(improvement, suffix=""):
    return f"{IMPROVEMENTS}/{improvement['id']}{suffix}"


def ok(res, status=200):
    assert res.status_code == status, res.get_json()
    return res.get_json()


def set_root_cause(client, improvement, cause_id, text="No cleaning standard for the panel"):
    return ok(client.put(url(improvement, "/root-cause"), json={"root_cause": text, "root_cause_id": cause_id}))


def add_action(client, improvement, owner, kind="corrective", text="Fit a sealed contact block"):
    detail = ok(client.post(url(improvement, "/actions"), json={
        "kind": kind, "text": text, "owner_id": owner["id"], "due_date": now_ist().date().isoformat()}), 201)
    return detail, detail["actions"][-1]


def mark_done(client, improvement, action, done_at=None, text="Fitted the sealed block"):
    body = {"done_text": text}
    if done_at is not None:
        body["done_at"] = done_at.strftime("%Y-%m-%dT%H:%M")
    return ok(client.post(url(improvement, f"/actions/{action['id']}/done"), json=body))


def cancel(client, improvement, action, reason="Not needed"):
    return ok(client.post(url(improvement, f"/actions/{action['id']}/cancel"), json={"reason": reason}))


def set_watch(client, improvement, days):
    return ok(client.put(url(improvement), json={"watch_days": days}))


def make_ready(client, person, improvement, cause_id, done_days=31):
    """Root cause, one corrective done ``done_days`` ago, a 30-day watch -> the detail (ready to verify)."""
    set_root_cause(client, improvement, cause_id)
    _, action = add_action(client, improvement, person)
    mark_done(client, improvement, action, minute(now_ist() - done_days * DAY))
    return set_watch(client, improvement, 30)


def verify(client, improvement, effective=True, **body):
    return client.post(url(improvement, f"/verify/{'effective' if effective else 'not-effective'}"), json=body)


def drop(client, improvement, reason="Duplicate of IM-2026-10-001"):
    return client.post(url(improvement, "/drop"), json={"reason": reason})


def events(detail, event):
    return [line for line in detail["timeline"] if line["event"] == event]


# ---------------------------------------------------------------------------
# The working states (§ 5.1)
# ---------------------------------------------------------------------------

class TestStates:

    def test_the_root_cause_moves_it_to_actions_open_with_a_line(self, eng, aged, no_cause):
        client, _ = eng
        improvement, _ = aged()
        detail = set_root_cause(client, improvement, no_cause)
        assert (detail["state"], detail["is_open"], detail["watch"]["from"]) == ("actions_open", True, None)
        line = events(detail, "state_changed")[0]
        assert (line["from_state"], line["to_state"], line["remark"]) == ("analysing", "actions_open", None)

    def test_done_starts_the_watch_and_a_lesson_does_not_end_or_move_it(self, eng, aged, no_cause):
        client, person = eng
        improvement, _ = aged()
        set_root_cause(client, improvement, no_cause)
        _, action = add_action(client, improvement, person)
        done_at = minute(now_ist() - 3 * DAY)
        detail = mark_done(client, improvement, action, done_at)
        assert (detail["state"], detail["watch"]["from"]) == ("watching", iso(done_at))
        assert detail["watch"]["until"] == iso(done_at + 90 * DAY) and detail["watch"]["ended"] is False
        detail, lesson = add_action(client, improvement, person, kind="lesson")
        assert (detail["state"], detail["watch"]["from"]) == ("watching", iso(done_at))
        detail = mark_done(client, improvement, lesson)
        assert (detail["state"], detail["watch"]["from"]) == ("watching", iso(done_at))

    def test_a_corrective_during_the_watch_ends_it_and_its_cancel_starts_it_again(self, eng, aged, no_cause):
        client, person = eng
        improvement, _ = aged()
        set_root_cause(client, improvement, no_cause)
        _, first = add_action(client, improvement, person)
        done_at = minute(now_ist() - 2 * DAY)
        mark_done(client, improvement, first, done_at)
        detail, second = add_action(client, improvement, person, kind="preventive")
        assert (detail["state"], detail["watch"]["from"]) == ("actions_open", None)
        detail = cancel(client, improvement, second)
        assert (detail["state"], detail["watch"]["from"]) == ("watching", iso(done_at))
        assert [(line["from_state"], line["to_state"]) for line in reversed(events(detail, "state_changed"))] == [
            ("analysing", "actions_open"), ("actions_open", "watching"), ("watching", "actions_open"),
            ("actions_open", "watching")]

    def test_all_cancelled_and_none_done_stays_actions_open(self, eng, aged, no_cause):
        client, person = eng
        improvement, _ = aged()
        set_root_cause(client, improvement, no_cause)
        _, action = add_action(client, improvement, person)
        assert cancel(client, improvement, action)["state"] == "actions_open"

    def test_done_before_the_root_cause_stays_analysing_then_the_root_cause_starts_the_watch(
            self, eng, aged, no_cause):
        client, person = eng
        improvement, _ = aged()
        _, action = add_action(client, improvement, person)
        done_at = minute(now_ist() - DAY)
        assert mark_done(client, improvement, action, done_at)["state"] == "analysing"
        detail = set_root_cause(client, improvement, no_cause)
        assert (detail["state"], detail["watch"]["from"]) == ("watching", iso(done_at))
        line = events(detail, "state_changed")[0]
        assert (line["from_state"], line["to_state"]) == ("analysing", "watching")

    def test_a_lesson_changed_into_a_machine_kind_ends_the_watch(self, eng, aged, no_cause):
        client, person = eng
        improvement, _ = aged()
        set_root_cause(client, improvement, no_cause)
        _, first = add_action(client, improvement, person)
        mark_done(client, improvement, first, minute(now_ist() - DAY))
        detail, lesson = add_action(client, improvement, person, kind="lesson")
        assert detail["state"] == "watching"
        detail = ok(client.put(url(improvement, f"/actions/{lesson['id']}"), json={"kind": "design_out"}))
        assert (detail["state"], detail["watch"]["from"]) == ("actions_open", None)


# ---------------------------------------------------------------------------
# Ready to verify (§ 5.2, D1)
# ---------------------------------------------------------------------------

class TestReady:

    def test_read_everywhere_from_the_clock_and_a_longer_watch_undoes_it(self, eng, aged, no_cause):
        client, person = eng
        improvement, ticket = aged()
        detail = make_ready(client, person, improvement, no_cause)
        assert (detail["state"], detail["is_open"], detail["watch"]["ended"]) == ("ready_to_verify", True, True)
        assert detail["can_verify"] and detail["can_drop"] and detail["can_add_note"] and detail["can_edit_watch"]
        items = ok(client.get(IMPROVEMENTS, query_string={"state": "open"}))["items"]
        assert next(i for i in items if i["id"] == improvement["id"])["state"] == "ready_to_verify"
        assert ticket_detail(client, ticket)["improvements"] == [
            {"id": improvement["id"], "serial": improvement["serial"], "state": "ready_to_verify"}]
        detail = set_watch(client, improvement, 60)
        assert (detail["state"], detail["watch"]["ended"], detail["can_verify"]) == ("watching", False, False)
        assert events(detail, "edited")[0]["remark"] == "Watch: 30 days → 60 days"

    def test_the_watch_days_refused(self, eng, aged):
        client, _ = eng
        improvement, _ = aged()
        for days in (29, 366, True, None):
            assert refusal(client.put(url(improvement), json={"watch_days": days})) == (
                400, "watch_days", "Choose a watch of 30 to 365 days")


# ---------------------------------------------------------------------------
# Close as effective
# ---------------------------------------------------------------------------

class TestCloseEffective:

    def test_the_lead_closes_it_and_its_ticket_may_start_another(self, eng, aged, no_cause, db_rows):
        client, person = eng
        improvement, ticket = aged()
        make_ready(client, person, improvement, no_cause)
        detail = ok(verify(client, improvement, remark="  Won't start did not come back  "))
        assert (detail["state"], detail["is_open"], detail["can_verify"], detail["can_drop"]) == (
            "closed_effective", False, False, False)
        assert {k: detail["closed"][k] for k in ("by_name", "by_lead", "remark")} == {
            "by_name": person["name"], "by_lead": True, "remark": "Won't start did not come back"}
        line = events(detail, "closed_effective")[0]
        assert (line["from_state"], line["to_state"], line["by_name"]) == (
            "ready_to_verify", "closed_effective", person["name"])
        assert [r["open_link"] for r in db_rows("SELECT open_link FROM improvement_tickets WHERE improvement_id = %s",
                                                (improvement["id"],))] == [None]
        assert ticket_detail(client, ticket)["can_start_improvement"] is True
        assert refusal(verify(client, improvement)) == (409, None, CLOSED)

    def test_a_manager_closing_is_not_the_lead_and_no_remark_is_null(self, eng, manager, aged, no_cause):
        client, person = eng
        improvement, _ = aged()
        make_ready(client, person, improvement, no_cause)
        detail = ok(verify(manager[0], improvement))
        assert (detail["closed"]["by_lead"], detail["closed"]["remark"], detail["closed"]["by_name"]) == (
            False, None, manager[1]["name"])

    def test_not_yet(self, eng, aged, no_cause):
        client, person = eng
        improvement, _ = aged()
        assert refusal(verify(client, improvement)) == (409, None, VERIFY_NOT_YET)
        set_root_cause(client, improvement, no_cause)
        assert refusal(verify(client, improvement)) == (409, None, VERIFY_NOT_YET)
        _, action = add_action(client, improvement, person)
        done_at = minute(now_ist() - DAY)
        mark_done(client, improvement, action, done_at)
        assert refusal(verify(client, improvement, effective=False, remark="x")) == (
            409, None, f"The watch ends on {done_at + 90 * DAY:%d-%m-%Y}. Verify after it.")

    def test_who_may_verify(self, eng, aged, no_cause, operator_at_site, operator_here, stranger):
        client, person = eng
        improvement, _ = aged()
        make_ready(client, person, improvement, no_cause)
        assert verify(operator_at_site[0], improvement).status_code == 403
        assert verify(operator_here, improvement).status_code == 403
        assert verify(stranger, improvement).status_code == 404
        assert get(client, improvement)["state"] == "ready_to_verify"


# ---------------------------------------------------------------------------
# Not effective: the follow-up
# ---------------------------------------------------------------------------

class TestNotEffective:

    def test_a_follow_up_with_the_same_tickets(self, eng, aged, no_cause, restored_ticket, db_rows):
        client, person = eng
        improvement, ticket = aged()
        other = restored_ticket()
        ok(add(client, improvement, other), 201)
        ok(client.post(url(improvement, "/whys"), json={"question": "Why?", "answer": "Dust"}), 201)
        make_ready(client, person, improvement, no_cause)
        assert refusal(verify(client, improvement, effective=False)) == (400, "remark", "Say why it did not work")
        res = verify(client, improvement, effective=False, remark="Won't start came back twice")
        follow_up = ok(res, 201)
        assert number(follow_up["serial"]) == number(improvement["serial"]) + 1
        assert (follow_up["state"], follow_up["is_open"], follow_up["title"], follow_up["problem"]) == (
            "analysing", True, improvement["title"], improvement["problem"])
        assert follow_up["lead"]["id"] == person["id"] and follow_up["watch"]["days"] == 30
        assert sorted(t["id"] for t in follow_up["tickets"]) == sorted([ticket["id"], other["id"]])
        assert follow_up["follow_up_of"] == {"id": improvement["id"], "serial": improvement["serial"]}
        assert (follow_up["whys"], follow_up["actions"], follow_up["root_cause"]) == ([], [], None)
        assert [(line["event"], line["remark"]) for line in reversed(follow_up["timeline"])][0] == (
            "started", f"Follow-up of {improvement['serial']}")
        assert sorted(line["ticket"]["id"] for line in events(follow_up, "ticket_linked")) == sorted(
            [ticket["id"], other["id"]])
        links = db_rows("SELECT improvement_id, open_link FROM improvement_tickets WHERE ticket_id = %s ORDER BY 1",
                        (ticket["id"],))
        assert [(r["improvement_id"], r["open_link"]) for r in links] == [(improvement["id"], None),
                                                                           (follow_up["id"], 1)]
        old = get(client, improvement)
        assert (old["state"], old["closed"]["remark"]) == ("closed_not_effective", "Won't start came back twice")
        assert old["follow_up"] == {"id": follow_up["id"], "serial": follow_up["serial"]}
        assert len(old["whys"]) == 1 and len(old["actions"]) == 1
        assert events(old, "closed_not_effective")[0]["to_state"] == "closed_not_effective"

    def test_a_link_committed_while_it_waited_goes_to_the_follow_up(self, eng, aged, no_cause, restored_ticket,
                                                                   db_rows, monkeypatch):
        """CR1-01: the counter's SELECT fixes the REPEATABLE READ snapshot before (6b) is held, so the old
        links must come from a locking read.  An add that held (6b) is played here by a link committed on a
        connection of its own right after the counter."""
        client, person = eng
        improvement, ticket = aged()
        make_ready(client, person, improvement, no_cause)
        late = restored_ticket()
        real_counter = improvements.next_counter

        def counter_then_a_late_link(cur, scope):
            number = real_counter(cur, scope)
            db_rows("INSERT INTO improvement_tickets (improvement_id, ticket_id, created_by) VALUES (%s, %s, %s)",
                    (improvement["id"], late["id"], "test"))
            return number
        monkeypatch.setattr(improvements, "next_counter", counter_then_a_late_link)
        follow_up = ok(verify(client, improvement, effective=False, remark="Came back"), 201)
        assert sorted(t["id"] for t in follow_up["tickets"]) == sorted([ticket["id"], late["id"]])

    def test_a_refused_one_leaves_no_serial_gap(self, eng, aged, restored_ticket):
        client, person = eng
        improvement, _ = aged()
        assert verify(client, improvement, effective=False, remark="No").status_code == 409
        assert number(started(client, restored_ticket(), person)["serial"]) == number(improvement["serial"]) + 1


# ---------------------------------------------------------------------------
# Drop (D10)
# ---------------------------------------------------------------------------

class TestDrop:

    def test_drop_cancels_the_open_countermeasures(self, eng, aged, operator_at_site):
        client, person = eng
        improvement, _ = aged()
        _, first = add_action(client, improvement, person)
        _, done = add_action(client, improvement, person, kind="preventive", text="Clean the panel weekly")
        _, last = add_action(client, improvement, person, kind="lesson", text="Tell the shift leads")
        done_before = mark_done(client, improvement, done)["actions"][1]
        assert sorted(i["id"] for i in ok(client.get(f"{IMPROVEMENTS}/actions/mine"))["items"]) == [
            first["id"], last["id"]]
        assert refusal(drop(client, improvement, "  ")) == (400, "reason", "Say why it is dropped")
        assert drop(operator_at_site[0], improvement).status_code == 403
        detail = ok(drop(client, improvement, "Merged into another improvement"))
        assert (detail["state"], detail["is_open"], detail["closed"]["remark"]) == (
            "dropped", False, "Merged into another improvement")
        by_id = {a["id"]: a for a in detail["actions"]}
        for action in (first, last):
            assert (by_id[action["id"]]["state"], by_id[action["id"]]["cancel_reason"]) == (
                "cancelled", "Dropped with the improvement: Merged into another improvement")
        def stored(action):   # the buttons' can_* flags follow the closed improvement; the row itself is kept
            return {k: v for k, v in action.items() if not k.startswith("can_")}
        assert stored(by_id[done["id"]]) == stored(done_before) and done_before["state"] == "done"
        # D10, (6c) by id: one line per cancelled countermeasure, in id order (the timeline is newest first)
        assert [line["action"]["id"] for line in reversed(events(detail, "action_cancelled"))] == [
            first["id"], last["id"]]
        line = events(detail, "dropped")[0]
        assert (line["from_state"], line["to_state"], line["remark"]) == (
            "analysing", "dropped", "Merged into another improvement")
        assert ok(client.get(f"{IMPROVEMENTS}/actions/mine"))["items"] == []
        assert refusal(drop(client, improvement)) == (409, None, CLOSED)
        assert ok(client.get(IMPROVEMENTS, query_string={"state": "closed"}))["items"][0]["id"] == improvement["id"]


# ---------------------------------------------------------------------------
# A closed improvement is read-only (D12)
# ---------------------------------------------------------------------------

class TestReadOnly:

    def test_every_write_answers_409(self, eng, aged, no_cause, restored_ticket):
        client, person = eng
        improvement, ticket = aged()
        ok(client.post(url(improvement, "/whys"), json={"question": "Why?", "answer": "Dust"}), 201)
        _, open_action = add_action(client, improvement, person, kind="lesson")
        detail = ok(drop(client, improvement))
        why = detail["whys"][0]
        action = f"/actions/{open_action['id']}"
        writes = [
            client.put(url(improvement), json={"title": "New"}),
            client.put(url(improvement), json={"watch_days": 60}),
            add(client, improvement, restored_ticket()),
            remove(client, improvement, ticket),
            client.post(url(improvement, "/whys"), json={"question": "Why?", "answer": "Dust"}),
            client.put(url(improvement, f"/whys/{why['id']}"), json={"answer": "Oil"}),
            client.delete(url(improvement, f"/whys/{why['id']}")),
            client.put(url(improvement, "/root-cause"), json={"root_cause": "x", "root_cause_id": no_cause}),
            client.post(url(improvement, "/actions"), json={"kind": "corrective", "text": "x", "owner_id": person["id"],
                                                            "due_date": now_ist().date().isoformat()}),
            client.put(url(improvement, action), json={"text": "y"}),
            client.post(url(improvement, f"{action}/done"), json={"done_text": "Done"}),
            client.post(url(improvement, f"{action}/cancel"), json={"reason": "No"}),
            upload_to(client, f"{IMPROVEMENTS}/actions/{open_action['id']}/documents", kind="photo", title="x",
                      data=JPEG, filename="x.jpg"),
            client.post(url(improvement, "/notes"), json={"remark": "Late"}),
            drop(client, improvement),
            verify(client, improvement),
            verify(client, improvement, effective=False, remark="x"),
        ]
        assert [refusal(res)[0::2] for res in writes] == [(409, CLOSED)] * len(writes)


# ---------------------------------------------------------------------------
# The watch's figures (§ 5.4)
# ---------------------------------------------------------------------------

class TestWatchFigures:

    def test_what_counts(self, eng, aged, no_cause, restored_ticket, make_ticket, make_equipment, unit, machine,
                         db_rows, modes):
        client, person = eng
        improvement, ticket = aged(days=50)
        set_root_cause(client, improvement, no_cause)
        _, action = add_action(client, improvement, person)
        watch_from = minute(now_ist() - 20 * DAY)
        mark_done(client, improvement, action, watch_from)

        def ticket_at(when, node=machine, mode=modes[0], intensity="critical", not_a_fault=0):
            t = make_ticket(node, intensity=intensity)
            db_rows("UPDATE tickets SET occurred_at = %s, failure_mode_id = %s, not_a_fault = %s WHERE id = %s",
                    (when, mode, not_a_fault, t["id"]))
            return t
        repeat = ticket_at(watch_from + 2 * DAY)
        ticket_at(watch_from + 3 * DAY, node=make_equipment(unit=unit))      # another machine: not counted
        ticket_at(watch_from + 4 * DAY, not_a_fault=1)                        # not a fault: not counted
        degraded = ticket_at(watch_from + 5 * DAY, intensity="degraded")
        ticket_at(watch_from + 6 * DAY, mode=modes[1])                        # another symptom
        figures = get(client, improvement)["watch"]["figures"]
        assert figures["machines"] == [{"id": machine["id"], "code": machine["code"]}]
        assert [s["id"] for s in figures["symptoms"]] == [modes[0]]
        assert (figures["before"]["days"], figures["before"]["breakdowns"], figures["before"]["symptom_breakdowns"]) == (
            90, 1, 1)
        assert (figures["after"]["days"], figures["after"]["breakdowns"], figures["after"]["symptom_breakdowns"]) == (
            20, 2, 1)
        assert [(r["id"], r["intensity"], r["in_watch"], r["machine_code"]) for r in figures["repeats"]] == [
            (repeat["id"], "critical", True, machine["code"]), (degraded["id"], "degraded", True, machine["code"])]

    def test_a_closed_improvements_figures_stop_at_the_close(self, eng, aged, no_cause, make_ticket, machine,
                                                             db_rows, modes):
        client, person = eng
        improvement, ticket = aged(days=45)
        make_ready(client, person, improvement, no_cause)
        closed = ok(verify(client, improvement))
        closed_at = datetime.strptime(closed["closed"]["at"], "%Y-%m-%dT%H:%M:%S+05:30")
        later = make_ticket(machine)
        db_rows("UPDATE tickets SET occurred_at = %s, failure_mode_id = %s WHERE id = %s",
                (closed_at + timedelta(minutes=1), modes[0], later["id"]))
        figures = get(client, improvement)["watch"]["figures"]
        assert figures["repeats"] == [] and figures["after"]["breakdowns"] == 0
        rows = db_rows("SELECT event, occurred_at, intensity, waiting_reason, machine_stopped FROM ticket_events"
                       " WHERE ticket_id = %s ORDER BY occurred_at, id", (ticket["id"],))
        assert figures["before"]["downtime_minutes"] == ticket_times(rows, closed_at)["downtime_minutes"]


class TestDatabaseDown:

    @pytest.fixture
    def made(self, aged):
        return aged()[0]

    def test_a_note_is_503(self, operator_at_site, made, db_down):
        """CR1-02: by a holder of improvement:note, so the 503 comes from the route's get_db()."""
        client, _ = operator_at_site
        assert client.post(url(made, "/notes"), json={"remark": "x"}).status_code == 503


def test_the_ticket_page_and_start_rule_after_a_drop(eng, aged, restored_ticket):
    """S067 D4: a dropped improvement frees its tickets."""
    client, person = eng
    improvement, ticket = aged()
    ok(drop(client, improvement))
    assert ticket_detail(client, ticket)["improvements"][0]["state"] == "dropped"
    assert start(client, ticket, person).status_code == 201
