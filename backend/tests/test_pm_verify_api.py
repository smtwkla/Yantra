"""Verify and send back a PM job (S099 § 5, § 6, § 8.2): Mark done's copy of the plan's setting and the second
done's floor, verify, send back, the plan's open job, the page's fields, the lock.  Needs the dev MariaDB container.

Each test makes its own site, unit, model and machine (test_pm_plans_api's press) and its plan through
POST /api/pm/plans as an engineer, saved past due (every 30 days, last done 40 days ago), so the save makes the job;
the technician starts it, fills it and marks it done by API (``done_job``).  The run (``generate``) settles every
plan of the worker's database, so a test that runs it first deactivates the others (``alone``).
"""

import threading
import time
from datetime import timedelta

import pytest

import config
from local_db import get_local_db
from pm_work_core import (
    ALREADY_VERIFIED, JOB_CANCELLED, NO_VERIFICATION, NOT_DONE_YET, REMARK_NOT_TEXT, REMARK_TOO_LONG, SEND_BACK_REMARK,
    open_job_cancelled, open_job_started,
)
from tests.test_pm_generate import alone, db_now, events_of, fix_now, generate, jobs_of
from tests.pm_helpers import (  # noqa: F401 — fixtures
    CHECK, SCRAPPED, TASK, _ok, add_model_meter, at_site, change, eng, engineer_a, hours, oil, other_site, press,
    site,
)
from tests.test_pm_work_api import (  # noqa: F401 — the tech fixture
    JOBS, READING, done, fill, minute, page, plan_with, refusal, start, tech,
)

LEAK = "Oil seeping at the left rod seal"
REWORK = "Re-tighten the left rod seal"
PLANS = "/api/pm/plans"


def done_job(engineer, tech_pair, node, db_rows, items=None, performer=None, **plan_fields):
    """A plan saved past due (a Check and a Task unless ``items``), its job started by the technician (``tech_pair``,
    (client, person)) for ``performer`` (default himself), the Check answered Not OK with a remark, a Task Done, a
    reading 45, and marked done -> (plan, the job's page answer)."""
    client, person = tech_pair
    plan, job = plan_with(engineer, node, db_rows, items=items or [CHECK, TASK], **plan_fields)
    body = start(client, job["id"], performer or person)
    answers = {"check": {"outcome": "not_ok", "remark": LEAK}, "task": {"outcome": "done"},
               "reading": {"value": "45"}}
    for item in body["items"]:
        fill(client, job["id"], item["id"], **answers[item["item_type"]])
    return plan, done(client, job["id"])


def verify(client, job_id, status=200, **body):
    return _ok(client.post(f"{JOBS}/{job_id}/verify", json=body), status)


def send_back(client, job_id, status=200, remark=REWORK):
    return _ok(client.post(f"{JOBS}/{job_id}/send-back", json={"remark": remark}), status)


def job_row(db_rows, job_id):
    return db_rows("SELECT * FROM pm_jobs WHERE id = %s", (job_id,))[0]


def line_of(body, event):
    """The page's last timeline line of ``event`` (the save's created line has seconds, so it may sort last)."""
    return [line for line in body["events"] if line["event"] == event][-1]


# ---------------------------------------------------------------------------
# Mark done copies the setting (§ 5.5)
# ---------------------------------------------------------------------------

class TestTheCopy:

    def test_a_maintenance_plan_s_job_waits_and_a_later_change_does_not_move_it(self, engineer_a, press, tech,
                                                                              db_rows):
        plan, job = done_job(engineer_a, tech, press, db_rows)
        assert (job["state"], job["needs_verification"], job["awaits_verification"]) == ("done", True, True)
        assert job_row(db_rows, job["id"])["needs_verification"] == 1
        change(engineer_a, plan, needs_verification=False)
        assert job_row(db_rows, job["id"])["needs_verification"] == 1
        assert page(engineer_a, job["id"])["awaits_verification"] is True

    def test_a_plan_that_needs_no_verification_ends_final(self, engineer_a, press, tech, db_rows):
        plan, job = done_job(engineer_a, tech, press, db_rows, needs_verification=False)
        assert (job["needs_verification"], job["awaits_verification"], job["can_verify"]) == (False, False, False)
        change(engineer_a, plan, needs_verification=True)
        assert job_row(db_rows, job["id"])["needs_verification"] == 0


# ---------------------------------------------------------------------------
# Verify job (§ 5.3)
# ---------------------------------------------------------------------------

class TestVerify:

    def test_an_engineer_of_the_site_verifies(self, eng, press, tech, db_rows):
        engineer, person = eng
        _, job = done_job(engineer, tech, press, db_rows)
        before = job_row(db_rows, job["id"])
        body = verify(engineer, job["id"], remark=" Checked the seal ")
        assert (body["state"], body["can_verify"], body["can_send_back"], body["can_work"]) == (
            "verified", False, False, False)
        assert body["verification"] == {"at": body["verification"]["at"], "by_name": person["name"],
                                        "remark": "Checked the seal", "self_verified": False}
        after = job_row(db_rows, job["id"])
        assert (after["done_at"], after["timeliness"], after["needs_verification"]) == (
            before["done_at"], before["timeliness"], 1)
        line = events_of(db_rows, job["id"])[-1]
        assert (line["event"], line["from_state"], line["to_state"], line["person_id"], line["remark"]) == (
            "verified", "done", "verified", person["id"], "Checked the seal")
        assert line_of(body, "verified")["self_verified"] is False
        assert line_of(body, "done")["self_verified"] is None

    def test_a_manager_verifies(self, engineer_a, press, tech, at_site, db_rows):
        _, job = done_job(engineer_a, tech, press, db_rows)
        assert verify(at_site("maint_manager"), job["id"])["state"] == "verified"

    def test_an_engineer_verifying_his_own_job_is_recorded(self, eng, press, tech, db_rows):
        engineer, person = eng
        _, job = done_job(engineer, tech, press, db_rows, performer=person)
        body = verify(engineer, job["id"])
        assert body["verification"]["self_verified"] is True
        assert line_of(body, "verified")["self_verified"] is True

    def test_admin_verifies_with_no_team_record(self, engineer_a, press, tech, keycloak_admin, db_rows):
        _, job = done_job(engineer_a, tech, press, db_rows)
        body = verify(keycloak_admin, job["id"])
        assert body["verification"]["self_verified"] is False
        assert events_of(db_rows, job["id"])[-1]["person_id"] is None

    def test_the_other_roles_are_refused(self, engineer_a, press, tech, at_site, role_client, db_rows):
        _, job = done_job(engineer_a, tech, press, db_rows)
        clients = [tech[0], at_site("maint_operator"), at_site("maint_supervisor"), at_site("maint_storekeeper"),
                   role_client("it_admin")]
        for client in clients:
            assert client.post(f"{JOBS}/{job['id']}/verify", json={}).status_code == 403
            assert client.post(f"{JOBS}/{job['id']}/send-back", json={"remark": REWORK}).status_code == 403
        assert job_row(db_rows, job["id"])["state"] == "done"

    def test_another_site_s_engineer_and_a_missing_job_get_404(self, engineer_a, press, tech, user_at_sites,
                                                               other_site, db_rows):
        _, job = done_job(engineer_a, tech, press, db_rows)
        stranger, _ = user_at_sites([(other_site, "maint_engineer", "all")])
        assert stranger.post(f"{JOBS}/{job['id']}/verify", json={}).status_code == 404
        assert engineer_a.post(f"{JOBS}/999999999/verify", json={}).status_code == 404

    def test_the_state_refusals(self, engineer_a, press, tech, db_rows):
        client, person = tech
        _, due = plan_with(engineer_a, press, db_rows, title="Due check")
        assert refusal(engineer_a.post(f"{JOBS}/{due['id']}/verify", json={})) == (409, None, NOT_DONE_YET)
        _, started = plan_with(engineer_a, press, db_rows, title="Started check")
        start(client, started["id"], person)
        assert refusal(engineer_a.post(f"{JOBS}/{started['id']}/verify", json={})) == (409, None, NOT_DONE_YET)
        _, job = done_job(engineer_a, tech, press, db_rows, title="Verified check")
        verify(engineer_a, job["id"])
        assert refusal(engineer_a.post(f"{JOBS}/{job['id']}/verify", json={})) == (409, None, ALREADY_VERIFIED)
        assert refusal(engineer_a.post(f"{JOBS}/{job['id']}/send-back", json={"remark": REWORK})) == (
            409, None, ALREADY_VERIFIED)
        _, final = done_job(engineer_a, tech, press, db_rows, title="Final check", needs_verification=False)
        assert refusal(engineer_a.post(f"{JOBS}/{final['id']}/verify", json={})) == (409, None, NO_VERIFICATION)
        db_rows("UPDATE pm_jobs SET needs_verification = NULL WHERE id = %s", (final["id"],))   # done before S099
        assert refusal(engineer_a.post(f"{JOBS}/{final['id']}/verify", json={})) == (409, None, NO_VERIFICATION)
        plan, cancelled = plan_with(engineer_a, press, db_rows, title="Cancelled check")
        change(engineer_a, plan, active=False)                       # cancels its due job (S097 D7)
        assert refusal(engineer_a.post(f"{JOBS}/{cancelled['id']}/verify", json={})) == (409, None, JOB_CANCELLED)

    def test_the_remark_refusals(self, engineer_a, press, tech, db_rows):
        _, job = done_job(engineer_a, tech, press, db_rows)
        assert refusal(engineer_a.post(f"{JOBS}/{job['id']}/verify", json={"remark": "x" * 501})) == (
            400, "remark", REMARK_TOO_LONG)
        assert refusal(engineer_a.post(f"{JOBS}/{job['id']}/verify", json={"remark": 5})) == (
            400, "remark", REMARK_NOT_TEXT)
        assert job_row(db_rows, job["id"])["state"] == "done"

    def test_a_machine_scrapped_after_done_is_still_verified(self, engineer_a, press, tech, db_rows):
        """D7: verify closes the record of work done before the scrap."""
        _, job = done_job(engineer_a, tech, press, db_rows)
        db_rows("UPDATE equipment SET lifecycle = 'scrapped' WHERE id = %s", (press["id"],))
        body = page(engineer_a, job["id"])
        assert (body["can_verify"], body["can_send_back"]) == (True, False)
        assert verify(engineer_a, job["id"])["state"] == "verified"


# ---------------------------------------------------------------------------
# Send back (§ 5.4)
# ---------------------------------------------------------------------------

class TestSendBack:

    def test_a_remark_is_needed(self, engineer_a, press, tech, db_rows):
        _, job = done_job(engineer_a, tech, press, db_rows)
        for remark in (None, "", "   "):
            assert refusal(engineer_a.post(f"{JOBS}/{job['id']}/send-back", json={"remark": remark})) == (
                400, "remark", SEND_BACK_REMARK)
        assert job_row(db_rows, job["id"])["state"] == "done"

    def test_sent_back_then_fixed_and_done_again(self, eng, press, tech, db_rows, monkeypatch):
        engineer, person = eng
        client, _ = tech
        plan, job = done_job(engineer, tech, press, db_rows)
        first = job_row(db_rows, job["id"])
        body = send_back(engineer, job["id"])
        assert (body["state"], body["can_verify"], body["done_at"], body["timeliness"]) == (
            "in_progress", False, None, None)
        assert body["sent_back"] == {"at": body["sent_back"]["at"], "by_name": person["name"], "remark": REWORK}
        stored = job_row(db_rows, job["id"])
        assert (stored["done_at"], stored["done_meter"], stored["timeliness"], stored["needs_verification"]) == (
            None, None, None, None)
        assert (stored["open_plan_id"], stored["started_at"], stored["performed_by_id"]) == (
            plan["id"], first["started_at"], first["performed_by_id"])
        line = events_of(db_rows, job["id"])[-1]
        assert (line["event"], line["from_state"], line["to_state"], line["person_id"], line["remark"]) == (
            "sent_back", "done", "in_progress", person["id"], REWORK)
        tech_page = page(client, job["id"])
        assert tech_page["can_work"] is True and tech_page["sent_back"]["remark"] == REWORK
        check = tech_page["items"][0]
        assert (check["outcome"], check["remark"]) == ("not_ok", LEAK)              # the results stay
        # The rework overwrites the first answer in place (BR1-03)
        fill(client, job["id"], check["id"], outcome="ok", remark=None)
        result = db_rows("SELECT outcome, remark FROM pm_job_results WHERE id = %s", (check["id"],))[0]
        assert (result["outcome"], result["remark"]) == ("ok", None)
        # The second done is at or after the send-back (BR1-02)
        sent_back_at = line["occurred_at"]
        assert refusal(client.post(f"{JOBS}/{job['id']}/done",
                                   json={"done_at": minute(sent_back_at - timedelta(minutes=1))})) == (
            400, "done_at", f"Done must be at or after it was sent back, {sent_back_at.strftime('%d-%m-%Y %H:%M')}.")
        later = db_now(db_rows).replace(second=0, microsecond=0) + timedelta(days=3)
        fix_now(monkeypatch, later)
        again = done(client, job["id"], done_at=minute(later))
        assert (again["state"], again["timeliness"], again["needs_verification"], again["awaits_verification"]) == (
            "done", "late", True, True)
        assert job_row(db_rows, job["id"])["done_at"] == later
        assert [e["event"] for e in events_of(db_rows, job["id"])] == [
            "created", "started", "done", "sent_back", "done"]
        # The plan's next due counts from the new done time (no open job: 30 days on)
        cards = _ok(engineer.get(PLANS, query_string={"equipment_id": press["id"]}))["items"]
        (card,) = [item for item in cards if item["id"] == plan["id"]]
        assert card["schedule"]["next_due"]["due_on"] == (later.date() + timedelta(days=30)).isoformat()

    def test_a_scrapped_machine_refuses_send_back(self, engineer_a, press, tech, db_rows):
        _, job = done_job(engineer_a, tech, press, db_rows)
        db_rows("UPDATE equipment SET lifecycle = 'scrapped' WHERE id = %s", (press["id"],))
        assert refusal(engineer_a.post(f"{JOBS}/{job['id']}/send-back", json={"remark": REWORK})) == (
            409, None, SCRAPPED)
        assert job_row(db_rows, job["id"])["state"] == "done"


# ---------------------------------------------------------------------------
# The plan's open job (§ 5.4 step 3, D3)
# ---------------------------------------------------------------------------

class TestTheOpenJob:

    def _next_job(self, db_rows, plan, monkeypatch, days):
        """The run with the clock ``days`` on makes the plan's next job -> its row (the open one)."""
        moment = db_now(db_rows).replace(second=0, microsecond=0) + timedelta(days=days)
        fix_now(monkeypatch, moment)
        generate()
        return next(j for j in jobs_of(db_rows, plan["id"]) if j["state"] in ("due", "in_progress"))

    def test_send_back_cancels_the_open_job_and_the_run_makes_it_again(self, engineer_a, press, tech, db_rows,
                                                                       monkeypatch):
        client, _ = tech
        plan, job = done_job(engineer_a, tech, press, db_rows)
        alone(db_rows, plan["id"])
        open_job = self._next_job(db_rows, plan, monkeypatch, 28)
        assert page(engineer_a, job["id"])["open_job"] == {"id": open_job["id"], "serial": open_job["serial"],
                                                           "state": "due"}
        assert send_back(engineer_a, job["id"])["state"] == "in_progress"
        cancelled = job_row(db_rows, open_job["id"])
        assert (cancelled["state"], cancelled["open_plan_id"]) == ("cancelled", None)
        line = events_of(db_rows, open_job["id"])[-1]
        assert (line["event"], line["from_state"], line["to_state"], line["remark"]) == (
            "cancelled", "due", "cancelled", open_job_cancelled(job["serial"]))
        again = done(client, job["id"])
        new_done = job_row(db_rows, job["id"])["done_at"]
        made = self._next_job(db_rows, plan, monkeypatch, 56)
        assert made["serial"] != open_job["serial"]
        assert made["due_on"] == new_done.date() + timedelta(days=30)
        assert again["state"] == "done"

    def test_a_started_open_job_refuses_send_back_and_verify_leaves_it(self, engineer_a, press, tech, db_rows,
                                                                        monkeypatch):
        client, person = tech
        plan, job = done_job(engineer_a, tech, press, db_rows)
        alone(db_rows, plan["id"])
        open_job = self._next_job(db_rows, plan, monkeypatch, 28)
        start(client, open_job["id"], person)
        lines = len(events_of(db_rows, job["id"])) + len(events_of(db_rows, open_job["id"]))
        assert refusal(engineer_a.post(f"{JOBS}/{job['id']}/send-back", json={"remark": REWORK})) == (
            409, None, open_job_started(open_job["serial"]))
        assert (job_row(db_rows, job["id"])["state"], job_row(db_rows, open_job["id"])["state"]) == (
            "done", "in_progress")
        assert len(events_of(db_rows, job["id"])) + len(events_of(db_rows, open_job["id"])) == lines
        body = page(engineer_a, job["id"])
        assert (body["can_verify"], body["can_send_back"], body["open_job"]["state"]) == (True, False, "in_progress")
        assert verify(engineer_a, job["id"])["state"] == "verified"
        assert job_row(db_rows, open_job["id"])["state"] == "in_progress"

    def test_two_jobs_waiting(self, engineer_a, press, tech, db_rows, monkeypatch):
        """BR1-04: J1 and J2 wait; the run made J3.  Send back J1 cancels J3; J2's send-back is then refused, naming
        J1.  J1 done again (at or after its send-back, so after J2's done) is the plan's latest done: J4 counts
        from it."""
        client, person = tech
        plan, j1 = done_job(engineer_a, tech, press, db_rows)
        alone(db_rows, plan["id"])
        j2 = self._next_job(db_rows, plan, monkeypatch, 28)
        body = start(client, j2["id"], person)
        for item in body["items"]:
            fill(client, j2["id"], item["id"], **{"check": {"outcome": "ok"}, "task": {"outcome": "done"}}[
                item["item_type"]])
        done(client, j2["id"])
        j3 = self._next_job(db_rows, plan, monkeypatch, 56)
        assert j3["id"] not in (j1["id"], j2["id"])
        send_back(engineer_a, j1["id"])
        assert job_row(db_rows, j3["id"])["state"] == "cancelled"
        assert refusal(engineer_a.post(f"{JOBS}/{j2['id']}/send-back", json={"remark": REWORK})) == (
            409, None, open_job_started(j1["serial"]))
        done(client, j1["id"])
        latest = job_row(db_rows, j1["id"])["done_at"]
        assert latest > job_row(db_rows, j2["id"])["done_at"]
        j4 = self._next_job(db_rows, plan, monkeypatch, 84)
        assert j4["id"] not in (j1["id"], j2["id"], j3["id"])
        assert j4["due_on"] == latest.date() + timedelta(days=30)


# ---------------------------------------------------------------------------
# The page (§ 6.2), the lock (§ 5.6), the database down
# ---------------------------------------------------------------------------

class TestPage:

    def test_a_waiting_job_s_fields(self, engineer_a, press, tech, db_rows):
        client, _ = tech
        high = {**READING, "max_value": "40"}
        _, job = done_job(engineer_a, tech, press, db_rows, items=[CHECK, TASK, high])
        body = page(engineer_a, job["id"])
        assert (body["can_verify"], body["can_send_back"], body["open_job"]) == (True, True, None)
        assert body["findings"] == {"not_ok": 1, "not_done": 0, "out_of_limits": 1}
        assert (body["verification"], body["sent_back"]) == (None, None)
        tech_page = page(client, job["id"])
        assert (tech_page["can_verify"], tech_page["can_send_back"]) == (False, False)
        assert tech_page["awaits_verification"] is True

    def test_a_job_never_started_has_zero_findings(self, engineer_a, press, db_rows):
        _, job = plan_with(engineer_a, press, db_rows)
        body = page(engineer_a, job["id"])
        assert body["findings"] == {"not_ok": 0, "not_done": 0, "out_of_limits": 0}
        assert (body["needs_verification"], body["awaits_verification"], body["can_verify"]) == (None, False, False)

    def test_verify_waits_for_the_plan_lock(self, engineer_a, press, tech, db_rows):
        """§ 5.6: (6e) is taken first: with the plan's row held by another connection, the verify waits."""
        plan, job = done_job(engineer_a, tech, press, db_rows)
        conn = get_local_db(config.DB_CONFIG)
        result = {}
        try:
            with conn.cursor() as cur:
                cur.execute("START TRANSACTION")
                cur.execute("SELECT id FROM pm_plans WHERE id = %s FOR UPDATE", (plan["id"],))
                worker = threading.Thread(
                    target=lambda: result.update(res=engineer_a.post(f"{JOBS}/{job['id']}/verify", json={})))
                worker.start()
                time.sleep(1)
                assert worker.is_alive(), "the verify did not wait for the plan lock"
                cur.execute("COMMIT")
            worker.join(timeout=30)
        finally:
            conn.close()
        assert result["res"].status_code == 200
        assert job_row(db_rows, job["id"])["state"] == "verified"

    def test_the_database_down(self, engineer_a, db_down):
        assert engineer_a.post(f"{JOBS}/1/verify", json={}).status_code == 503
        assert engineer_a.post(f"{JOBS}/1/send-back", json={"remark": REWORK}).status_code == 503
