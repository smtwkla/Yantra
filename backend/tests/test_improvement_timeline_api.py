"""The timeline (S072 § 5.6, § 8.2): the line every write of S067, S069, S070 and S072 writes, the notes, the
order and the computed *Watch ended* line, against the test DB.  Needs the dev MariaDB container.
"""

from datetime import timedelta

import pytest

from tests.test_improvement_close_api import (  # noqa: F401  (fixtures used by name)
    DAY, add_action, aged, cancel, drop, events, make_ready, manager, mark_done, minute, modes, ok, operator_at_site,
    set_root_cause, set_watch, url,
)
from tests.test_improvements_api import (  # noqa: F401  (fixtures used by name)
    add, eng, get, no_cause, other_site, remove, restored_ticket, site,
)
from tests.ticket_helpers import now_ist, refusal


def oldest_first(detail):
    return list(reversed(detail["timeline"]))


def shape(line):
    return line["event"], line["remark"], line["earlier"]


class TestS067Lines:

    def test_a_start_writes_started_then_ticket_linked(self, eng, aged):
        _, person = eng
        improvement, ticket = aged()
        lines = oldest_first(improvement)
        assert [(line["event"], line["ticket"]) for line in lines] == [
            ("started", None), ("ticket_linked", {"id": ticket["id"], "serial": ticket["serial"]})]
        assert {line["by_name"] for line in lines} == {person["name"]}
        assert all(line["id"] is not None and line["action"] is None for line in lines)

    def test_an_edit_names_old_and_new_and_a_put_with_no_change_writes_nothing(self, eng, aged, manager):
        client, person = eng
        improvement, _ = aged()
        detail = ok(client.put(url(improvement), json={"title": "Dust trips the contactor"}))
        assert shape(events(detail, "edited")[0]) == ("edited", "Title: Contactor trips → Dust trips the contactor",
                                                      None)
        detail = ok(client.put(url(improvement), json={"lead_id": manager[1]["id"], "problem": "Dust and heat"}))
        assert events(detail, "edited")[0]["remark"] == (
            f"Problem: Dust in the panel → Dust and heat\nLead: {person['name']} → {manager[1]['name']}")
        detail = ok(client.put(url(improvement), json={"title": "Dust trips the contactor", "watch_days": 90}))
        assert len(events(detail, "edited")) == 2

    def test_add_and_remove_a_ticket(self, eng, aged, restored_ticket):
        client, _ = eng
        improvement, _ = aged()
        other = restored_ticket()
        ok(add(client, improvement, other), 201)
        detail = ok(remove(client, improvement, other))
        assert [(line["event"], line["ticket"]["id"]) for line in oldest_first(detail)[2:]] == [
            ("ticket_linked", other["id"]), ("ticket_removed", other["id"])]


class TestS069Lines:

    def why(self, client, improvement, question, answer, evidence=None):
        return ok(client.post(url(improvement, "/whys"), json={"question": question, "answer": answer,
                                                              "evidence": evidence}), 201)

    def test_add_change_move_and_remove_a_why(self, eng, aged):
        client, _ = eng
        improvement, _ = aged()
        self.why(client, improvement, "Why does it trip?", "Dust on the contacts")
        detail = self.why(client, improvement, "Why is there dust?", "The seal is torn", "Photo")
        assert events(detail, "why_added")[0]["remark"] == "2. Why is there dust? Because: The seal is torn Evidence: Photo"
        first, second = detail["whys"]
        detail = ok(client.put(url(improvement, f"/whys/{first['id']}"), json={"answer": "Dust and oil"}))
        assert shape(events(detail, "why_changed")[0]) == (
            "why_changed", "1. Why does it trip? Because: Dust and oil", "1. Why does it trip? Because: Dust on the contacts")
        detail = ok(client.put(url(improvement, f"/whys/{second['id']}"), json={"position": 1}))
        changed = events(detail, "why_changed")
        assert len(changed) == 2   # the moved why only; the other's shift writes none
        assert shape(changed[0]) == ("why_changed", "1. Why is there dust? Because: The seal is torn Evidence: Photo",
                                     "2. Why is there dust? Because: The seal is torn Evidence: Photo")
        detail = ok(client.delete(url(improvement, f"/whys/{first['id']}")))
        assert shape(events(detail, "why_removed")[0]) == ("why_removed", None, "2. Why does it trip? Because: Dust and oil")
        detail = ok(client.put(url(improvement, f"/whys/{second['id']}"), json={"answer": "The seal is torn"}))
        assert len(events(detail, "why_changed")) == 2   # nothing changed: no line

    def test_the_root_cause_set_then_changed(self, eng, aged, no_cause, db_rows):
        client, _ = eng
        improvement, _ = aged()
        cause = db_rows("SELECT code, label FROM failure_causes WHERE id = %s", (no_cause,))[0]
        detail = set_root_cause(client, improvement, no_cause, "No cleaning standard")
        assert shape(events(detail, "root_cause_set")[0]) == (
            "root_cause_set", f"{cause['code']} {cause['label']}: No cleaning standard", None)
        detail = ok(client.put(url(improvement, "/root-cause"), json={
            "root_cause": "No cleaning standard", "root_cause_id": no_cause, "contributing_causes": "Old seal"}))
        assert shape(events(detail, "root_cause_changed")[0]) == (
            "root_cause_changed", f"{cause['code']} {cause['label']}: No cleaning standard\nOther causes: Old seal",
            f"{cause['code']} {cause['label']}: No cleaning standard")
        detail = ok(client.put(url(improvement, "/root-cause"), json={
            "root_cause": "No cleaning standard", "root_cause_id": no_cause}))
        assert len(events(detail, "root_cause_changed")) == 1


class TestS070Lines:

    def test_add_change_done_cancel(self, eng, aged, manager):
        client, person = eng
        improvement, _ = aged()
        detail, action = add_action(client, improvement, person)
        line = events(detail, "action_added")[0]
        today = now_ist().date()
        assert line["remark"] == (f"Corrective: Fit a sealed contact block. Owner {person['name']} (engineer),"
                                  f" due {today:%d-%m-%Y}.")
        assert line["action"] == {"id": action["id"], "kind": "corrective", "text": "Fit a sealed contact block"}
        due = today + timedelta(days=3)
        detail = ok(client.put(url(improvement, f"/actions/{action['id']}"), json={
            "kind": "preventive", "owner_id": manager[1]["id"], "due_date": due.isoformat()}))
        assert shape(events(detail, "action_changed")[0]) == (
            "action_changed", f"Kind: Corrective → Preventive\nOwner: {person['name']} → {manager[1]['name']}\n"
                              f"Due: {today:%d-%m-%Y} → {due:%d-%m-%Y}", None)
        detail = ok(client.put(url(improvement, f"/actions/{action['id']}"), json={"kind": "preventive"}))
        assert len(events(detail, "action_changed")) == 1
        done_at = minute(now_ist() - 2 * DAY)
        detail = mark_done(client, improvement, action, done_at, "Cleaned and sealed")
        done = events(detail, "action_done")[0]
        assert (done["remark"], done["occurred_at"]) == ("Cleaned and sealed", done_at.strftime("%Y-%m-%dT%H:%M:%S+05:30"))
        # Back-dated: it sorts by its time, below the lines written today
        assert detail["timeline"].index(done) > detail["timeline"].index(events(detail, "action_changed")[0])
        _, second = add_action(client, improvement, person, kind="lesson")
        detail = cancel(client, improvement, second, "Covered by the SOP")
        assert shape(events(detail, "action_cancelled")[0]) == ("action_cancelled", "Covered by the SOP", None)


class TestNotes:

    def test_who_may_add_a_note(self, eng, aged, operator_at_site, role_client, user_at_sites, site):
        client, _ = eng
        improvement, _ = aged()
        operator, person = operator_at_site
        detail = ok(operator.post(url(improvement, "/notes"), json={"remark": "  Panel cleaned on\nnight shift  "}), 201)
        note = events(detail, "note")[0]
        assert (note["remark"], note["by_name"]) == ("Panel cleaned on\nnight shift", person["name"])
        assert detail["can_add_note"] is True
        assert role_client("it_admin").post(url(improvement, "/notes"), json={"remark": "x"}).status_code == 403
        assert get(role_client("it_admin"), improvement)["can_add_note"] is False
        storekeeper, _ = user_at_sites([(site, "maint_storekeeper", "all")])
        assert storekeeper.post(url(improvement, "/notes"), json={"remark": "x"}).status_code == 403
        assert refusal(operator.post(url(improvement, "/notes"), json={"remark": "x" * 1001})) == (
            400, "remark", "Note: up to 1000 characters")
        ok(drop(client, improvement))
        assert refusal(operator.post(url(improvement, "/notes"), json={"remark": "Late"})) == (
            409, None, "This improvement is closed")


class TestWatchEnded:

    def test_shown_when_ready_not_while_watching(self, eng, aged, no_cause):
        client, person = eng
        improvement, _ = aged()
        detail = make_ready(client, person, improvement, no_cause)
        ended = events(detail, "watch_ended")
        assert len(ended) == 1 and ended[0]["id"] is None and ended[0]["by_name"] is None
        assert ended[0]["occurred_at"] == detail["watch"]["until"]
        # The watch ended a day ago: below the lines written today
        assert detail["timeline"].index(ended[0]) > detail["timeline"].index(events(detail, "edited")[0])
        assert events(set_watch(client, improvement, 60), "watch_ended") == []

    @pytest.mark.parametrize("days", [31])
    def test_kept_after_the_close(self, eng, aged, no_cause, days):
        client, person = eng
        improvement, _ = aged()
        make_ready(client, person, improvement, no_cause, done_days=days)
        detail = ok(client.post(url(improvement, "/verify/effective"), json={}))
        assert [line["event"] for line in detail["timeline"][:1]] == ["closed_effective"]
        assert len(events(detail, "watch_ended")) == 1
