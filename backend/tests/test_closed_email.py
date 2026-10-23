"""*Ticket closed* by email, end to end short of the mail server (S032 § 5.1–5.5, § 8 Backend): what
a close enqueues, the fan-out to the site's managers with an address, and email_send's outcomes
with a fake sender.  No test reaches a mail server: the session's SMTP values are reserved test
values (conftest smtp_test_values) and every send here is a fake.

The recipients are real people, memberships and person_units rows, as in test_alerts.py.
"""

import json
import smtplib
import ssl
from datetime import timedelta

import pytest

import config
import mail_sender
from email_core import duration_text
import task_handlers
from local_db import get_local_db
from task_handlers import NoRetry, email_send, ticket_alert
from tests.conftest import TICKETS
from tests.db_names import TEST_WORKER_LOCK as TEST_LOCK
from tests.test_alerts import run, tasks
from tests.ticket_helpers import local, now_ist
from worker import Worker


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _url(ticket, *parts):
    return "/".join([f"{TICKETS}/{ticket['id']}", *parts])


def _ok(res, status=200):
    assert res.status_code == status, res.get_json()
    return res.get_json()


def email_sends(db_rows, person_ids=None):
    """The email_send tasks -> their payloads (and max_attempts), oldest first; only these people's
    when ``person_ids`` is given."""
    rows = db_rows("SELECT payload, max_attempts FROM task_queue WHERE task_type = 'email_send' ORDER BY id")
    sends = [{**json.loads(row["payload"]), "max_attempts": row["max_attempts"]} for row in rows]
    return sends if person_ids is None else [s for s in sends if s["person_id"] in person_ids]


@pytest.fixture
def codes(db_rows):
    """A cause, an action and a symptom from the seeded lists (S016)."""
    one = lambda sql: db_rows(sql)[0]  # noqa: E731
    return {"cause": one("SELECT id, label FROM failure_causes WHERE code = '3.4'"),
            "no_cause": one("SELECT id, label FROM failure_causes WHERE code = '5.1'"),
            "action": one("SELECT id, label FROM maintenance_actions WHERE code = '1'"),
            "mode": one("SELECT id, label FROM failure_modes WHERE code = 'NOI'")}


@pytest.fixture
def plant(make_site, make_unit, make_equipment, user_at_sites, db_rows):
    """A site with the machine's unit and a second unit, and the people around it: who should
    and who should not get the closed-ticket email.  Every one has an address but the manager
    without one."""
    site = make_site()
    unit, other_unit = make_unit(site=site), make_unit(site=site)
    machine = make_equipment(unit=unit)
    people = {}
    for key, spec in {
        "manager": [(site, "maint_manager", "all")],
        "manager_unit": [(site, "maint_manager", [unit])],
        "manager_other_unit": [(site, "maint_manager", [other_unit])],
        "manager_no_email": [(site, "maint_manager", "all")],
        "manager_inactive": [(site, "maint_manager", "all")],
        "engineer": [(site, "maint_engineer", "all")],
        "closer": [(site, "maint_manager", "all")],
    }.items():
        client, person = user_at_sites(spec)
        people[key] = {"client": client, "person": person}
        if key != "manager_no_email":
            db_rows("UPDATE people SET email = %s WHERE id = %s", (f"{key}.{person['id']}@example.test", person["id"]))
    db_rows("UPDATE people SET active = 0 WHERE id = %s", (people["manager_inactive"]["person"]["id"],))
    db_rows("DELETE FROM task_queue")
    return {"site": site, "unit": unit, "machine": machine, "people": people}


def pid(plant, key):
    return plant["people"][key]["person"]["id"]


def restored_ticket(plant, client=None, when=None, **raise_body):
    """A breakdown raised, started and back in service, with one labour row by the closer ->
    the ticket's detail.  ``when`` (a naive IST datetime) back-dates the raise; the later
    events follow it by an hour each."""
    client = client or plant["people"]["closer"]["client"]
    body = {"equipment_id": plant["machine"]["id"], "intensity": "critical", "description": "Oil leak at the seal",
            **raise_body}
    times = {}
    if when is not None:
        body["occurred_at"] = local(when)
        times = {"start": {"occurred_at": local(when + timedelta(hours=1))},
                 "restore": {"occurred_at": local(when + timedelta(hours=2))}}
    ticket = _ok(client.post(TICKETS, json=body), 201)
    _ok(client.post(_url(ticket, "moves", "start"), json=times.get("start", {})))
    _ok(client.post(_url(ticket, "moves", "restore"), json={"person_id": pid(plant, "closer"), **times.get("restore", {})}))
    work_date = (when or now_ist()).date().isoformat()
    _ok(client.post(_url(ticket, "labour"), json={"person_id": pid(plant, "closer"), "work_date": work_date,
                                                  "minutes": 90}), 201)
    return ticket


def close(plant, ticket, codes, client=None, **extra):
    client = client or plant["people"]["closer"]["client"]
    return client.post(_url(ticket, "moves", "close"), json={"cause_id": codes["cause"]["id"],
                                                             "action_id": codes["action"]["id"],
                                                             "failure_mode_id": codes["mode"]["id"],
                                                             "remark": "Seal changed", **extra})


def closed_alert(db_rows, ticket):
    return [t for t in tasks(db_rows, "ticket_alert", ticket["id"]) if t["payload"]["kind"] == "closed"]


# ---------------------------------------------------------------------------
# What a close enqueues (§ 1.3)
# ---------------------------------------------------------------------------

class TestEnqueue:

    def test_a_close_queues_one_closed_alert_without_the_closer(self, plant, codes, db_rows):
        ticket = restored_ticket(plant)
        done = _ok(close(plant, ticket, codes))
        closed_event = [e["id"] for e in done["events"] if e["event"] == "closed"][-1]
        (alert,) = closed_alert(db_rows, ticket)
        assert alert["payload"] == {"ticket_id": ticket["id"], "kind": "closed", "event_id": closed_event,
                                    "exclude_person_ids": [pid(plant, "closer")]}

    def test_a_refused_close_queues_nothing(self, plant, codes, db_rows):
        client = plant["people"]["closer"]["client"]
        ticket = _ok(client.post(TICKETS, json={"equipment_id": plant["machine"]["id"], "intensity": "critical",
                                                "description": "Stopped"}), 201)
        _ok(client.post(_url(ticket, "moves", "restore"), json={"person_id": pid(plant, "closer")}))
        assert close(plant, ticket, codes).status_code == 409      # no labour yet
        assert closed_alert(db_rows, ticket) == []

    def test_not_a_fault_queues_it_too_and_says_so(self, plant, codes, db_rows):
        client = plant["people"]["closer"]["client"]
        ticket = _ok(client.post(TICKETS, json={"equipment_id": plant["machine"]["id"], "intensity": "degraded",
                                                "description": "Noise"}), 201)
        _ok(client.post(_url(ticket, "moves", "not-a-fault"), json={"cause_id": codes["no_cause"]["id"],
                                                                   "remark": "Ran fine when I got there"}))
        (alert,) = closed_alert(db_rows, ticket)
        run(ticket_alert, alert["payload"])
        (sent,) = email_sends(db_rows, [pid(plant, "manager")])
        assert sent["subject"] == (f"Closed as not a fault · {plant['site']['code']}.{plant['unit']['code']} · "
                                   f"{plant['machine']['code']} · {ticket['serial']}")
        assert sent["body"].startswith(f"{ticket['serial']} — Defect, closed as not a fault\n")
        assert "Ran fine when I got there" in sent["body"] and "Labour:" not in sent["body"]

    def test_a_close_back_dated_8_days_queues_nothing(self, plant, codes, db_rows, keycloak_admin):
        """S028: the admin may enter history; a close more than 7 days back sends nothing."""
        when = now_ist() - timedelta(days=10)
        ticket = restored_ticket(plant, client=keycloak_admin, when=when)
        _ok(close(plant, ticket, codes, client=keycloak_admin, occurred_at=local(now_ist() - timedelta(days=8))))
        assert closed_alert(db_rows, ticket) == []


# ---------------------------------------------------------------------------
# The fan-out (§ 5.1, § 5.2)
# ---------------------------------------------------------------------------

class TestFanOut:

    def _drain(self, plant, codes, db_rows):
        ticket = restored_ticket(plant)
        _ok(close(plant, ticket, codes))
        (alert,) = closed_alert(db_rows, ticket)
        run(ticket_alert, alert["payload"])
        return ticket

    def test_the_sites_managers_with_an_address_covering_the_unit(self, plant, codes, db_rows):
        """Two managers covering the unit (all units, that unit); not the one at the other unit,
        the engineer, the manager with no address, the inactive one, or the closer."""
        ticket = self._drain(plant, codes, db_rows)
        sends = email_sends(db_rows)
        assert sorted(s["person_id"] for s in sends) == sorted([pid(plant, "manager"), pid(plant, "manager_unit")])
        subject = (f"Closed · {plant['site']['code']}.{plant['unit']['code']} · {plant['machine']['code']} · "
                   f"{ticket['serial']}")
        assert {s["subject"] for s in sends} == {subject}
        assert {s["max_attempts"] for s in sends} == {3}
        # A.5.34: no address in the queue
        assert "@" not in json.dumps(sends)

    def test_the_body_holds_the_close(self, plant, codes, db_rows):
        ticket = self._drain(plant, codes, db_rows)
        body = email_sends(db_rows)[0]["body"]
        closer = plant["people"]["closer"]["person"]["name"].split()[0]
        assert body.startswith(f"{ticket['serial']} — Breakdown, closed\n")
        assert f"Cause:            {codes['cause']['label']}\n" in body
        assert f"Action:           {codes['action']['label']}\n" in body
        assert "Labour:           1 h 30 min, 1 person\n" in body
        # The symptom chosen at the close, then the description
        assert f"Problem:          {codes['mode']['label']} — Oil leak at the seal\n" in body
        assert f"by {closer}\n" in body and "Remark:           Seal changed\n" in body
        assert body.endswith(f"/tickets/{ticket['id']}\n")
        for label in ("Downtime:", "Repair time:", "Back in service:"):
            assert label in body

    def test_the_figures_match_the_ticket_page(self, plant, codes, db_rows):
        ticket = self._drain(plant, codes, db_rows)
        times = _ok(plant["people"]["closer"]["client"].get(_url(ticket)))["times"]
        body = email_sends(db_rows)[0]["body"]
        assert f"Downtime:         {duration_text(times['downtime_minutes'])}\n" in body

    def test_nobody_with_an_address_reads_no_facts(self, plant, codes, db_rows, monkeypatch):
        """BR1-15: the extra facts are read only when someone will get the email."""
        db_rows("UPDATE people SET email = NULL")
        called = []
        monkeypatch.setattr(task_handlers.alerts, "read_closed_facts", lambda *a: called.append(a))
        self._drain(plant, codes, db_rows)
        assert email_sends(db_rows) == [] and called == []

    def test_email_off_at_alert_time_queues_no_send(self, plant, codes, db_rows, email_off):
        self._drain(plant, codes, db_rows)
        assert email_sends(db_rows) == []

    def test_no_push_for_a_closed_ticket(self, plant, codes, db_rows):
        self._drain(plant, codes, db_rows)
        assert db_rows("SELECT id FROM task_queue WHERE task_type = 'push_send'") == ()


# ---------------------------------------------------------------------------
# email_send with a fake sender (§ 5.5)
# ---------------------------------------------------------------------------

def fake_send(calls, error=None):
    def send(to, subject, body):
        calls.append((to, subject, body))
        if error is not None:
            raise error
    return send


@pytest.fixture
def person(make_person, db_rows):
    made = make_person()
    db_rows("UPDATE people SET email = 'arun@example.test' WHERE id = %s", (made["id"],))
    return made


def _payload(person):
    return {"person_id": person["id"], "subject": "Closed · S.U · M · TK-1", "body": "TK-1 — Breakdown, closed\n"}


class TestEmailSend:

    def test_sent_to_the_address_read_now(self, person):
        calls = []
        run(email_send, _payload(person), send=fake_send(calls))
        assert calls == [("arun@example.test", "Closed · S.U · M · TK-1", "TK-1 — Breakdown, closed\n")]

    def test_a_refused_recipient_fails_at_once_without_the_address(self, person, caplog):
        calls = []
        refused = smtplib.SMTPRecipientsRefused({"arun@example.test": (550, b"no such user")})
        with pytest.raises(NoRetry) as raised:
            run(email_send, _payload(person), send=fake_send(calls, refused))
        assert str(raised.value) == "email refused (SMTP 550)"
        assert raised.value.__cause__ is None and raised.value.__suppress_context__
        assert "example.test" not in caplog.text
        assert f"email_send: person {person['id']} not sent: email refused (SMTP 550)" in caplog.text

    @pytest.mark.parametrize("error, text", [
        (TimeoutError("timed out"), "mail server not reached (TimeoutError)"),
        (smtplib.SMTPRecipientsRefused({"arun@example.test": (451, b"greylisted")}), "email deferred (SMTP 451)"),
    ])
    def test_a_network_fault_or_a_4xx_retries(self, person, error, text):
        with pytest.raises(RuntimeError) as raised:
            run(email_send, _payload(person), send=fake_send([], error))
        assert type(raised.value) is RuntimeError and str(raised.value) == text

    def test_a_wrong_password_fails_at_once(self, person):
        with pytest.raises(NoRetry, match=r"email refused \(SMTP 535\)"):
            run(email_send, _payload(person), send=fake_send([], smtplib.SMTPAuthenticationError(535, b"bad")))

    def test_no_address_now_is_done_and_not_sent(self, person, db_rows):
        db_rows("UPDATE people SET email = NULL WHERE id = %s", (person["id"],))
        calls = []
        run(email_send, _payload(person), send=fake_send(calls))
        assert calls == []

    def test_an_inactive_person_is_done_and_not_sent(self, person, db_rows):
        db_rows("UPDATE people SET active = 0 WHERE id = %s", (person["id"],))
        calls = []
        run(email_send, _payload(person), send=fake_send(calls))
        assert calls == []

    def test_email_off_is_no_retry(self, person, email_off):
        calls = []
        with pytest.raises(NoRetry, match="email is not set up on this server"):
            run(email_send, _payload(person), send=fake_send(calls))
        assert calls == []

    @pytest.mark.parametrize("payload", [{"person_id": "x", "subject": "s", "body": "b"}, {"person_id": 1},
                                         {"person_id": 1, "subject": None, "body": "b"}])
    def test_a_malformed_task_is_a_bad_task(self, payload):
        with pytest.raises(task_handlers.BadTask):
            run(email_send, payload)

    def test_through_the_worker_a_refusal_fails_once_and_keeps_no_address(self, person, db_rows, monkeypatch):
        refused = smtplib.SMTPRecipientsRefused({"arun@example.test": (550, b"no such user")})
        monkeypatch.setattr(mail_sender, "send", fake_send([], refused))
        db_rows("DELETE FROM task_queue")
        conn = get_local_db(config.DB_CONFIG)
        worker = Worker(config.DB_CONFIG, lock_name=TEST_LOCK)
        try:
            with conn.cursor() as cur:
                task_id = task_handlers.enqueue(cur, "email_send", _payload(person), max_attempts=3)
            worker.connect()
            assert worker.run_one() == task_id
            row = db_rows("SELECT status, attempts, last_error FROM task_queue WHERE id = %s", (task_id,))[0]
            assert row == {"status": "failed", "attempts": 1, "last_error": "NoRetry: email refused (SMTP 550)"}
        finally:
            worker.close()
            conn.close()
            db_rows("DELETE FROM task_queue")


class TestSender:
    """mail_sender with smtplib.SMTP replaced: STARTTLS with a checked certificate, the login, one
    message to one recipient, the settings read at call time."""

    def test_starttls_login_and_one_message(self, monkeypatch):
        seen = {}

        class FakeSMTP:
            def __init__(self, host, port, timeout):
                seen["connect"] = (host, port, timeout)

            def starttls(self, context):
                seen["verify"] = context.verify_mode

            def login(self, user, password):
                seen["login"] = (user, password)

            def send_message(self, message):
                seen["message"] = (message["From"], message["To"], message["Subject"], message.get_content())

            def quit(self):
                seen["quit"] = True

            def close(self):
                seen["close"] = True

        monkeypatch.setattr(mail_sender.smtplib, "SMTP", FakeSMTP)
        mail_sender.send("arun@example.test", "Subject", "Body\n")
        assert seen["connect"] == ("smtp.example.test", 2525, 30)
        assert seen["verify"] == ssl.CERT_REQUIRED
        assert seen["login"] == ("yantra-test", "test-password")
        assert seen["message"] == ("yantra@example.test", "arun@example.test", "Subject", "Body\n")
        assert seen["quit"] and seen["close"]

    @pytest.mark.parametrize("quit_error", [smtplib.SMTPResponseException(421, b"closing"),
                                            smtplib.SMTPResponseException(554, b"bye"),
                                            smtplib.SMTPServerDisconnected("gone"), OSError("reset")])
    def test_a_quit_failure_after_the_message_is_accepted_is_not_raised(self, monkeypatch, quit_error):
        seen = {"sent": 0}

        class FakeSMTP:
            def __init__(self, host, port, timeout):
                pass

            def starttls(self, context):
                pass

            def login(self, user, password):
                pass

            def send_message(self, message):
                seen["sent"] += 1

            def quit(self):
                raise quit_error

            def close(self):
                seen["close"] = True

        monkeypatch.setattr(mail_sender.smtplib, "SMTP", FakeSMTP)
        mail_sender.send("arun@example.test", "Subject", "Body\n")
        assert seen == {"sent": 1, "close": True}

    def test_through_email_send_a_quit_failure_leaves_the_task_done_with_no_retry(self, person, monkeypatch):
        sends = []

        class FakeSMTP:
            def __init__(self, host, port, timeout):
                pass

            def starttls(self, context):
                pass

            def login(self, user, password):
                pass

            def send_message(self, message):
                sends.append(message["To"])

            def quit(self):
                raise smtplib.SMTPResponseException(421, b"closing")

            def close(self):
                pass

        monkeypatch.setattr(mail_sender.smtplib, "SMTP", FakeSMTP)
        run(email_send, _payload(person))  # no exception: the task is done
        assert len(sends) == 1

    def test_an_error_before_the_message_is_still_raised(self, monkeypatch):
        closed = []

        class FakeSMTP:
            def __init__(self, host, port, timeout):
                pass

            def starttls(self, context):
                pass

            def login(self, user, password):
                raise smtplib.SMTPAuthenticationError(535, b"bad login")

            def send_message(self, message):
                pass

            def quit(self):
                raise AssertionError("no QUIT after a failure before the send")

            def close(self):
                closed.append(True)

        monkeypatch.setattr(mail_sender.smtplib, "SMTP", FakeSMTP)
        with pytest.raises(smtplib.SMTPAuthenticationError):
            mail_sender.send("arun@example.test", "Subject", "Body\n")
        assert closed == [True]

    @pytest.mark.parametrize("name", ["SMTP_HOST", "SMTP_PORT", "SMTP_FROM"])
    def test_enabled_needs_host_port_and_sender(self, monkeypatch, name):
        assert mail_sender.enabled()
        monkeypatch.setattr(config, name, 0 if name == "SMTP_PORT" else "")
        assert not mail_sender.enabled()
