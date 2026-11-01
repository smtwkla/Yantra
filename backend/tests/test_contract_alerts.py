"""Contract reminders (S084 § 8.2), against the test DB, short of the push service and the mail server.  Needs the
dev MariaDB container.

The daily scan (contract_reminder_scan) queues one contract_alert per reminder due and marks it (v46);
contract_alert sends it by push to the holders of contract:read and by email to the holders of contract:read_senior
at the sites of the contract's machines (S087; every site for a contract with no machine).  The handlers run here on a
connection of their own, in a transaction as the worker runs
them (test_alerts.run); the worker itself runs only where draining every task is the point, with both senders
faked, so no test reaches a push service or a mail server (no_real_push, smtp_test_values).

Each test makes its own site and contract with a machine there (through the API, as IT admin), then sets the dates
relative to the
database's CURDATE() with db_rows, so the kept worker database is the starting state.  The scan reads every
contract of the database: a test asserts only on its own contract's tasks and rows, and the all-or-nothing test
runs one scan first so only its own rows are candidates.
"""

import json
from contextlib import contextmanager

import pytest

import alerts
import config
import mail_sender
import push_sender
import worker as worker_module
from local_db import get_local_db
from task_handlers import BadTask, contract_alert, contract_reminder_scan
from tests.db_names import TEST_WORKER_LOCK as TEST_LOCK
# add_device: a fixture used by name
from tests.test_alerts import add_device, fake_send as fake_push, run  # noqa: F401
from tests.test_closed_email import fake_send as fake_mail
from worker import Worker

CONTRACTS = "/api/contracts"
TITLE_60 = "Contract ends in 60 days · {site}"


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def site(make_site):
    return make_site()


@pytest.fixture
def vendor(make_vendor):
    return make_vendor()


@pytest.fixture
def contract(admin, site, vendor, uniq, db_rows, machine_at):
    """contract(days_left=60, at=[the site], **fields) -> a new contract (the API's answer) ending ``days_left``
    days after the database's today, started 300 days before it, with one machine at each site of ``at`` (S087: a
    contract's sites are its machines'; ``at=[]`` makes one with no machine)."""
    def make(days_left=60, at=None, **fields):
        body = {"vendor_id": vendor["id"], "contract_type": "amc",
                "title": f"AMC {uniq.vendor_name()}", "contract_number": "TEST/AMC/0001",
                "from_date": "2026-01-01", "to_date": "2026-12-31", **fields}
        res = admin.post(CONTRACTS, json=body)
        assert res.status_code == 201, res.get_json()
        made = res.get_json()
        for at_site in ([site] if at is None else at):
            res = admin.post(f"{CONTRACTS}/{made['id']}/equipment", json={"equipment_id": machine_at(at_site)["id"]})
            assert res.status_code == 201, res.get_json()
        set_dates(db_rows, made, days_left)
        return made
    return make


@pytest.fixture
def machine_at(make_equipment, make_unit):
    """machine_at(site) -> a new machine in a new unit of the site."""
    return lambda at: make_equipment(unit=make_unit(site=at))


def set_dates(db_rows, contract, days_left, started_days_ago=300):
    db_rows("UPDATE contracts SET from_date = CURDATE() - INTERVAL %s DAY, to_date = CURDATE() + INTERVAL %s DAY"
            " WHERE id = %s", (started_days_ago, days_left, contract["id"]))


@pytest.fixture
def people(user_at_sites, site, make_site, add_device, db_rows):
    """The people around the site of the contract's machine, each with one device: an engineer, a manager with an
    address, a manager without, a technician, a manager of another site -> {name: (person, device)}."""
    other = make_site()
    spec = {"engineer": (site, "maint_engineer"), "manager": (site, "maint_manager"),
            "manager_no_email": (site, "maint_manager"), "technician": (site, "maint_technician"),
            "other_manager": (other, "maint_manager")}
    made = {}
    for name, (at, role) in spec.items():
        _client, person = user_at_sites([(at, role, "all")])
        made[name] = (person, add_device(person))
    for name in ("manager", "other_manager", "engineer"):
        db_rows("UPDATE people SET email = %s WHERE id = %s", (f"{name}-{made[name][0]['id']}@example.test",
                                                                made[name][0]["id"]))
    return made


def alert_tasks(db_rows, contract_id):
    rows = db_rows("SELECT id, status, payload FROM task_queue WHERE task_type = 'contract_alert'"
                   " AND JSON_EXTRACT(payload, '$.contract_id') = %s ORDER BY id", (contract_id,))
    return [{**row, "payload": json.loads(row["payload"])} for row in rows]


def push_sends(db_rows, contract_id):
    rows = db_rows("SELECT status, payload FROM task_queue WHERE task_type = 'push_send'"
                   " AND JSON_UNQUOTE(JSON_EXTRACT(payload, '$.path')) = %s ORDER BY id",
                   (f"/contracts/{contract_id}",))
    return [{**json.loads(row["payload"]), "status": row["status"]} for row in rows]


def email_sends(db_rows, person_ids):
    if not person_ids:
        return []
    rows = db_rows("SELECT status, payload FROM task_queue WHERE task_type = 'email_send'"
                   f" AND JSON_EXTRACT(payload, '$.person_id') IN ({', '.join(['%s'] * len(person_ids))}) ORDER BY id",
                   list(person_ids))
    return [{**json.loads(row["payload"]), "status": row["status"]} for row in rows]


def markers(db_rows, contract):
    return db_rows("SELECT to_date, first_reminder_for, second_reminder_for, updated_at FROM contracts WHERE id = %s",
                   (contract["id"],))[0]


def scan():
    run(contract_reminder_scan, None)


def drain(db_rows, contract_id):
    """Run every pending contract_alert of the contract, as the worker would."""
    for task in alert_tasks(db_rows, contract_id):
        if task["status"] == "pending":
            run(contract_alert, task["payload"])
            db_rows("UPDATE task_queue SET status = 'done' WHERE id = %s", (task["id"],))


def payload_of(contract, row):
    return {"kind": "contract_ending", "contract_id": contract["id"], "to_date": row["to_date"].isoformat()}


# ---------------------------------------------------------------------------
# Not in the API (BS1-01)
# ---------------------------------------------------------------------------

class TestNotInTheApi:

    def test_the_markers_are_not_sent(self, contract, admin, site, db_rows):
        made = contract()
        scan()
        assert markers(db_rows, made)["first_reminder_for"] is not None
        one = admin.get(f"{CONTRACTS}/{made['id']}").get_json()
        assert "first_reminder_for" not in one and "second_reminder_for" not in one
        listed = admin.get(f"{CONTRACTS}?site_id={site['id']}&status=all").get_json()["items"]   # its machine's site
        (row,) = [c for c in listed if c["id"] == made["id"]]
        assert "first_reminder_for" not in row and "second_reminder_for" not in row


# ---------------------------------------------------------------------------
# The scan (§ 5.1, § 5.3)
# ---------------------------------------------------------------------------

class TestScan:

    def test_60_days_queues_the_first_once(self, contract, db_rows):
        made = contract(60)
        before = markers(db_rows, made)
        scan()
        (task,) = alert_tasks(db_rows, made["id"])
        row = markers(db_rows, made)
        assert task["payload"] == payload_of(made, row)
        assert row["first_reminder_for"] == row["to_date"] and row["second_reminder_for"] is None
        assert row["updated_at"] == before["updated_at"]
        scan()
        assert len(alert_tasks(db_rows, made["id"])) == 1

    def test_15_days_after_the_first_queues_the_second(self, contract, db_rows):
        made = contract(60)
        scan()
        set_dates(db_rows, made, 15)
        db_rows("UPDATE contracts SET first_reminder_for = to_date WHERE id = %s", (made["id"],))
        scan()
        assert len(alert_tasks(db_rows, made["id"])) == 2
        row = markers(db_rows, made)
        assert row["second_reminder_for"] == row["to_date"]

    def test_10_days_nothing_sent_queues_only_the_second(self, contract, db_rows):
        made = contract(10)
        scan()
        assert len(alert_tasks(db_rows, made["id"])) == 1
        row = markers(db_rows, made)
        assert row["second_reminder_for"] == row["to_date"] and row["first_reminder_for"] is None
        scan()
        assert len(alert_tasks(db_rows, made["id"])) == 1

    def test_nothing_outside_the_window(self, contract, db_rows):
        later = contract(61)
        ended = contract(-1)
        not_started = contract(30)
        set_dates(db_rows, not_started, 30, started_days_ago=-1)
        inactive = contract(30)
        db_rows("UPDATE contracts SET active = 0 WHERE id = %s", (inactive["id"],))
        scan()
        for made in (later, ended, not_started, inactive):
            assert alert_tasks(db_rows, made["id"]) == []
            assert markers(db_rows, made)["first_reminder_for"] is None

    def test_the_candidates_leave_out_a_first_sent_with_more_than_15_days(self, contract, db_rows):
        """BR1-12: a contract with its first reminder sent for this To date is no candidate until 15 days."""
        made = contract(30)
        db_rows("UPDATE contracts SET first_reminder_for = to_date WHERE id = %s", (made["id"],))
        today = db_rows("SELECT CURDATE() AS d")[0]["d"]
        with _cursor() as cur:
            assert made["id"] not in alerts.contract_scan_candidates(cur, today)
        set_dates(db_rows, made, 15)
        db_rows("UPDATE contracts SET first_reminder_for = to_date WHERE id = %s", (made["id"],))
        with _cursor() as cur:
            assert made["id"] in alerts.contract_scan_candidates(cur, today)


class TestRenewed:

    def _renewal(self, admin, site, vendor, made, db_rows, active):
        res = admin.post(CONTRACTS, json={"vendor_id": vendor["id"], "contract_type": "amc",
                                          "title": "AMC renewal", "from_date": "2026-01-01", "to_date": "2026-12-31"})
        assert res.status_code == 201, res.get_json()
        renewal = res.get_json()
        # R02.4 will set renewal_of_id; until then the test does (§ 5.2).  The renewal ends in 400 days.
        set_dates(db_rows, renewal, 400)
        db_rows("UPDATE contracts SET renewal_of_id = %s, active = %s WHERE id = %s",
                (made["id"], 1 if active else 0, renewal["id"]))

    def test_an_active_renewal_stops_the_reminder(self, contract, admin, site, vendor, db_rows):
        made = contract(60)
        self._renewal(admin, site, vendor, made, db_rows, active=True)
        scan()
        assert alert_tasks(db_rows, made["id"]) == []

    def test_an_inactive_renewal_does_not(self, contract, admin, site, vendor, db_rows):
        made = contract(60)
        self._renewal(admin, site, vendor, made, db_rows, active=False)
        scan()
        assert len(alert_tasks(db_rows, made["id"])) == 1


class TestReArm:

    def test_a_later_to_date_then_60_days_again(self, contract, db_rows):
        made = contract(60)
        scan()
        set_dates(db_rows, made, 90)
        scan()
        assert len(alert_tasks(db_rows, made["id"])) == 1
        # 30 days on, the new To date has 60 days left: shown here by moving the To date and the marker
        # (the old To date, now 30 days before the new one) back by 30 days, as the clock cannot move
        set_dates(db_rows, made, 60)
        db_rows("UPDATE contracts SET first_reminder_for = CURDATE() + INTERVAL 30 DAY WHERE id = %s", (made["id"],))
        scan()
        assert len(alert_tasks(db_rows, made["id"])) == 2
        row = markers(db_rows, made)
        assert row["first_reminder_for"] == row["to_date"]

    def test_an_earlier_to_date_queues_the_second(self, contract, db_rows):
        made = contract(60)
        scan()
        set_dates(db_rows, made, 10)
        scan()
        assert len(alert_tasks(db_rows, made["id"])) == 2
        row = markers(db_rows, made)
        assert row["second_reminder_for"] == row["to_date"]


class TestAllOrNothing:

    def test_a_fault_on_the_second_contract_keeps_nothing(self, contract, db_rows, monkeypatch):
        scan()   # every older candidate of the kept database is marked now
        one, two = contract(60), contract(60)
        queued = []
        real = alerts.enqueue_contract_alert

        def enqueue(cur, contract_id, to_date):
            if queued:
                raise RuntimeError("test: the second contract fails")
            queued.append(contract_id)
            return real(cur, contract_id, to_date)

        monkeypatch.setattr(alerts, "enqueue_contract_alert", enqueue)
        with pytest.raises(RuntimeError):
            scan()
        for made in (one, two):
            assert alert_tasks(db_rows, made["id"]) == []
            assert markers(db_rows, made)["first_reminder_for"] is None


# ---------------------------------------------------------------------------
# The alert task (§ 5.4, § 5.6)
# ---------------------------------------------------------------------------

class TestHandler:

    def test_push_to_engineers_and_managers_of_the_machine_s_site(self, contract, people, site, db_rows):
        made = contract(60)
        scan()
        drain(db_rows, made["id"])
        sent = push_sends(db_rows, made["id"])
        devices = sorted(s["subscription_id"] for s in sent)
        assert devices == sorted(people[name][1] for name in ("engineer", "manager", "manager_no_email"))
        for one in sent:
            assert one["title"] == TITLE_60.format(site=site["code"])
            assert one["body"].endswith("Renew it, or let it end.")
            assert (one["urgency"], one["ttl"], one["path"], one["tag"]) == (
                "low", 86400, f"/contracts/{made['id']}", f"contract-{made['id']}")

    def test_email_to_the_managers_with_an_address(self, contract, people, db_rows):
        made = contract(60)
        scan()
        drain(db_rows, made["id"])
        ids = [people[name][0]["id"] for name in people]
        (mail,) = email_sends(db_rows, ids)
        assert mail["person_id"] == people["manager"][0]["id"]
        assert mail["subject"].startswith("Contract ends on ") and made["title"] in mail["subject"]
        assert "@" not in json.dumps(mail)
        assert "TEST/AMC/0001" in mail["body"] and "/contracts/" in mail["body"]

    def test_a_manager_with_no_units_gets_both(self, contract, user_at_sites, site, add_device, db_rows):
        # The API refuses a membership with no units, so it is made here (all_units = 0, no person_units)
        _client, person = user_at_sites([(site, "maint_manager", "all")])
        db_rows("UPDATE memberships SET all_units = 0 WHERE person_id = %s", (person["id"],))
        device = add_device(person)
        db_rows("UPDATE people SET email = %s WHERE id = %s", (f"nounits-{person['id']}@example.test", person["id"]))
        made = contract(60)
        scan()
        drain(db_rows, made["id"])
        assert device in [s["subscription_id"] for s in push_sends(db_rows, made["id"])]
        assert len(email_sends(db_rows, [person["id"]])) == 1

    @pytest.mark.parametrize("change", [
        "UPDATE contracts SET active = 0 WHERE id = %s",
        "UPDATE contracts SET to_date = to_date + INTERVAL 5 DAY WHERE id = %s",
        "UPDATE contracts SET to_date = CURDATE() - INTERVAL 1 DAY WHERE id = %s",
    ])
    def test_no_longer_true_sends_nothing(self, contract, people, db_rows, change):
        made = contract(60)
        scan()
        db_rows(change, (made["id"],))
        drain(db_rows, made["id"])
        assert push_sends(db_rows, made["id"]) == []
        assert email_sends(db_rows, [people[name][0]["id"] for name in people]) == []

    def test_renewed_before_it_runs_sends_nothing(self, contract, people, admin, site, vendor, db_rows):
        made = contract(60)
        scan()
        TestRenewed()._renewal(admin, site, vendor, made, db_rows, active=True)
        drain(db_rows, made["id"])
        assert push_sends(db_rows, made["id"]) == []
        assert email_sends(db_rows, [people[name][0]["id"] for name in people]) == []

    def test_push_to_the_holders_at_each_machine_site(self, contract, user_at_sites, make_site, add_device, db_rows):
        """S087 § 5.6: lines at A and B -> the engineers and managers of both, each once (one holding roles at both
        sites too); not those of a third site."""
        a, b, c = make_site(), make_site(), make_site()
        spec = {"engineer_a": [(a, "maint_engineer", "all")], "manager_b": [(b, "maint_manager", "all")],
                "both": [(a, "maint_engineer", "all"), (b, "maint_manager", "all")],
                "technician_a": [(a, "maint_technician", "all")], "manager_c": [(c, "maint_manager", "all")]}
        devices = {}
        for name, memberships in spec.items():
            _client, person = user_at_sites(memberships)
            devices[name] = add_device(person)
        made = contract(60, at=[a, b])
        scan()
        drain(db_rows, made["id"])
        sent = push_sends(db_rows, made["id"])
        assert sorted(s["subscription_id"] for s in sent) == sorted(
            devices[name] for name in ("engineer_a", "manager_b", "both"))
        assert {s["title"] for s in sent} == {f"Contract ends in 60 days · {', '.join(sorted([a['code'], b['code']]))}"}

    def test_email_to_the_managers_at_each_machine_site(self, contract, user_at_sites, make_site, db_rows):
        a, b, c = make_site(), make_site(), make_site()
        managers = {}
        for name, at in (("a", a), ("b", b), ("c", c)):
            _client, person = user_at_sites([(at, "maint_manager", "all")])
            db_rows("UPDATE people SET email = %s WHERE id = %s", (f"m{name}-{person['id']}@example.test",
                                                                   person["id"]))
            managers[name] = person["id"]
        made = contract(60, at=[a, b])
        scan()
        drain(db_rows, made["id"])
        mails = email_sends(db_rows, list(managers.values()))
        assert sorted(m["person_id"] for m in mails) == sorted([managers["a"], managers["b"]])
        sites = ", ".join(sorted([a["code"], b["code"]]))
        assert all(m["subject"].endswith(f"({sites})") and f"Sites:            {sites}" in m["body"] for m in mails)

    def test_no_line_reaches_every_site(self, contract, people, db_rows):
        """S087 Q2 a: a contract with no machine goes to the holders at every site, so it is never lost; its texts
        name no site."""
        made = contract(60, at=[])
        scan()
        drain(db_rows, made["id"])
        sent = push_sends(db_rows, made["id"])
        devices = {s["subscription_id"] for s in sent}
        assert {people[name][1] for name in ("engineer", "manager", "manager_no_email", "other_manager")} <= devices
        assert people["technician"][1] not in devices
        assert {s["title"] for s in sent} == {"Contract ends in 60 days"}
        mailed = {m["person_id"] for m in email_sends(db_rows, [people[n][0]["id"] for n in people])}
        assert mailed == {people["manager"][0]["id"], people["other_manager"][0]["id"]}

    def test_push_off_email_only(self, contract, people, db_rows, push_off):
        made = contract(60)
        scan()
        drain(db_rows, made["id"])
        assert push_sends(db_rows, made["id"]) == []
        assert len(email_sends(db_rows, [people["manager"][0]["id"]])) == 1

    def test_email_off_push_only(self, contract, people, db_rows, email_off):
        made = contract(60)
        scan()
        drain(db_rows, made["id"])
        assert len(push_sends(db_rows, made["id"])) == 3
        assert email_sends(db_rows, [people[name][0]["id"] for name in people]) == []

    def test_both_off_no_rows_and_the_scan_still_marks(self, contract, people, db_rows, push_off, email_off):
        """D7: the markers are about the event, so turning a channel on later sends no backlog."""
        made = contract(60)
        scan()
        row = markers(db_rows, made)
        assert row["first_reminder_for"] == row["to_date"]
        drain(db_rows, made["id"])
        assert push_sends(db_rows, made["id"]) == []
        assert email_sends(db_rows, [people[name][0]["id"] for name in people]) == []


# ---------------------------------------------------------------------------
# Through the worker (§ 8.2)
# ---------------------------------------------------------------------------

@pytest.fixture
def queue_emptied(db_rows):
    """The worker drains every due task: start and end with an empty queue (as test_worker.py)."""
    db_rows("DELETE FROM task_queue")
    yield
    db_rows("DELETE FROM task_queue")


class TestThroughTheWorker:

    def test_scan_alert_and_sends_all_done(self, contract, people, site, db_rows, monkeypatch, queue_emptied):
        made = contract(60)
        other = contract(60, at=[])  # no machine: it reminds every site, so the worker sends it too (S091)
        pushed, mailed = [], []
        monkeypatch.setattr(push_sender, "send", fake_push(201, calls=pushed))
        monkeypatch.setattr(mail_sender, "send", fake_mail(mailed))
        monkeypatch.setattr(worker_module, "SCHEDULE", [("contract_reminder_scan", "00:00")])
        worker = Worker(config.DB_CONFIG, lock_name=TEST_LOCK, clock=lambda: db_rows("SELECT NOW() AS now")[0]["now"])
        try:
            assert worker.run_once() is True
        finally:
            worker.close()
        assert [r["status"] for r in db_rows("SELECT status FROM task_queue"
                                              " WHERE task_type = 'contract_reminder_scan'")] == ["done"]
        assert [t["status"] for t in alert_tasks(db_rows, made["id"])] == ["done"]
        assert {s["status"] for s in push_sends(db_rows, made["id"])} == {"done"}
        mine = [c for c in pushed if c[0] == people["engineer"][1] and c[1]["path"] == f"/contracts/{made['id']}"]
        assert len(mine) == 1 and mine[0][1]["title"] == TITLE_60.format(site=site["code"])
        assert mine[0][2:] == ("low", 86400)
        address = db_rows("SELECT email FROM people WHERE id = %s", (people["manager"][0]["id"],))[0]["email"]
        to_manager = [m for m in mailed if m[0] == address and made["title"] in m[1]]
        assert len(to_manager) == 1


# ---------------------------------------------------------------------------
# Bad tasks
# ---------------------------------------------------------------------------

class TestBadTasks:

    def test_the_scan_takes_no_payload(self):
        with pytest.raises(BadTask):
            run(contract_reminder_scan, {"x": 1})

    @pytest.mark.parametrize("payload", [
        {"kind": "nonsense", "contract_id": 1, "to_date": "2027-03-31"},
        {"kind": "contract_ending", "to_date": "2027-03-31"},
        {"kind": "contract_ending", "contract_id": 1, "to_date": "31-03-2027"},
        {"kind": "contract_ending", "contract_id": 1},
    ])
    def test_a_bad_payload(self, payload):
        with pytest.raises(BadTask):
            run(contract_alert, payload)

    def test_a_bad_to_date_names_the_task(self):
        with pytest.raises(BadTask, match="contract_alert needs to_date"):
            run(contract_alert, {"kind": "contract_ending", "contract_id": 1, "to_date": "x"})

    def test_a_missing_contract(self):
        with pytest.raises(BadTask, match="no contract"):
            run(contract_alert, {"kind": "contract_ending", "contract_id": 999999999, "to_date": "2027-03-31"})


@contextmanager
def _cursor():
    """A cursor on a connection of its own, closed with it (a plain read, outside the API)."""
    conn = get_local_db(config.DB_CONFIG)
    try:
        with conn.cursor() as cur:
            yield cur
    finally:
        conn.close()
