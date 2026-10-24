"""Meter readings (S039 § 5, § 6): log, history, remove, and the last reading on the meters list,
against the test DB.  Needs the dev MariaDB container (tooling/dev/dev-db-up.bat).  Every test
makes its own meter types and nodes (S038's fixtures).
"""

import threading
import time
from datetime import timedelta

import pytest

import config
from local_db import get_local_db
from tests.ticket_helpers import api_time, local, now_ist

EQUIPMENT = "/api/equipment"
SCRAPPED = "This record is scrapped and cannot be changed"
NOT_ON_NODE = "This machine does not have this meter. Reload the page."
LOWER = ("Lower than the reading of {when} ({shown}). Check the value, or tick Meter reset if the meter was"
         " reset.")


def _readings(node, reading=None):
    base = f"{EQUIPMENT}/{node['id']}/readings"
    return base if reading is None else f"{base}/{reading['id']}"


def _ok(res, status=200):
    assert res.status_code == status, res.get_json()
    return res.get_json()


def _refusal(res):
    body = res.get_json()
    return res.status_code, body.get("field"), body["error"]


def _minutes_ago(minutes):
    """A whole minute well in the past, so the server's clock never ticks past it mid-test."""
    return now_ist().replace(second=0, microsecond=0) - timedelta(minutes=minutes)


def _post(client, node, meter_type, value, minutes_ago=None, **body):
    data = {"meter_type_id": meter_type["id"], "value": value, **body}
    if minutes_ago is not None:
        data["taken_at"] = local(_minutes_ago(minutes_ago))
    return client.post(_readings(node), json=data)


def _log(client, node, meter_type, value, minutes_ago=None, **body):
    return _ok(_post(client, node, meter_type, value, minutes_ago, **body), 201)


def _history(client, node, meter_type, **query):
    args = "&".join(f"{k}={v}" for k, v in {"meter_type_id": meter_type["id"], **query}.items())
    return _ok(client.get(f"{_readings(node)}?{args}"))


def _add_own(admin, node, meter_type, **limits):
    _ok(admin.post(f"{EQUIPMENT}/{node['id']}/meters", json={"meter_type_id": meter_type["id"], **limits}), 201)
    return meter_type


@pytest.fixture
def engineer(at_unit):
    return at_unit("maint_engineer")


@pytest.fixture
def hours(admin, node, make_meter_type):
    """A counter on the node: Run hours, 1 decimal."""
    return _add_own(admin, node, make_meter_type(kind="counter", unit="h", decimals=1))


@pytest.fixture
def oil(admin, node, make_meter_type):
    """A gauge on the node, 10–60 °C."""
    return _add_own(admin, node, make_meter_type(), min_value="10", max_value="60")


@pytest.fixture
def shift(admin, node, make_meter_type):
    """An amount per period on the node: pieces of a shift."""
    return _add_own(admin, node, make_meter_type(kind="amount", unit="pcs", decimals=0))


@pytest.fixture
def oil_ok(admin, node, make_meter_type):
    """A Yes / No meter on the node, expected Yes."""
    return _add_own(admin, node, make_meter_type(kind="yes_no", expected_answer="yes"))


class TestLog:

    def test_an_operator_logs_a_reading_at_their_unit(self, operator, node, hours, db_rows):
        taken_at = _minutes_ago(10)
        reading = _log(operator, node, hours, "12345.6", 10, note="  end of shift ")
        assert set(reading) == {"id", "value", "taken_at", "is_reset", "limit_state", "note", "created_by",
                                "created_at", "removed_at", "removed_by"}
        assert (reading["value"], reading["taken_at"], reading["is_reset"], reading["limit_state"], reading["note"],
                reading["removed_at"]) == ("12345.6", api_time(taken_at), False, None, "end of shift", None)
        row = db_rows("SELECT value, source, created_by FROM meter_readings WHERE id = %s", (reading["id"],))[0]
        assert (str(row["value"]), row["source"], row["created_by"]) == ("12345.600", "manual", reading["created_by"])

    def test_without_a_time_the_servers_minute_is_taken(self, operator, node, hours):
        before = now_ist().replace(second=0, microsecond=0)
        taken_at = _log(operator, node, hours, "5")["taken_at"]
        assert taken_at.endswith(":00+05:30")
        assert api_time(before) <= taken_at <= api_time(before + timedelta(minutes=1))

    def test_the_supervisor_and_the_maintenance_ladder_log(self, at_unit, node, hours):
        for minutes, role in enumerate(("maint_supervisor", "maint_technician", "maint_engineer", "maint_manager")):
            _log(at_unit(role), node, hours, str(10 + minutes), 60 - minutes)

    def test_who_may_not_log(self, at_unit, admin, node, hours):
        for client in (at_unit("maint_storekeeper"), admin):    # IT admin holds no reading:log (U2)
            assert _post(client, node, hours, "5").status_code == 403

    def test_at_another_site_is_403(self, user_at_sites, make_site, unit, node, hours):
        """Reading:log held at another site only: the node's site refuses, naming it."""
        client, _ = user_at_sites([({"id": unit["site_id"]}, "maint_storekeeper", [unit]),
                                   (make_site(), "maint_operator", "all")])
        status, _, message = _refusal(_post(client, node, hours, "5"))
        assert status == 403 and message.startswith("You can't do this at ")

    def test_an_unknown_node_and_one_outside_the_units_are_404(self, operator, user_with_units, make_unit, node,
                                                                hours):
        assert operator.post(f"{EQUIPMENT}/999999999/readings", json={"meter_type_id": hours["id"],
                                                                     "value": "1"}).status_code == 404
        outsider = user_with_units("maint_operator", [make_unit()])
        assert _post(outsider, node, hours, "1").status_code == 404

    def test_a_meter_not_on_the_node_is_409(self, operator, node, make_meter_type):
        other = make_meter_type(kind="counter", unit="h")
        assert _refusal(_post(operator, node, other, "1")) == (409, "meter_type_id", NOT_ON_NODE)

    def test_a_scrapped_node_is_409(self, operator, admin, node, hours):
        _ok(admin.put(f"{EQUIPMENT}/{node['id']}", json={"lifecycle": "scrapped"}))
        assert _refusal(_post(operator, node, hours, "1")) == (409, None, SCRAPPED)

    def test_the_same_minute_is_409(self, operator, node, hours):
        _log(operator, node, hours, "5", 30)
        assert _refusal(_post(operator, node, hours, "6", 30)) == (
            409, "taken_at", "A reading at this time exists. Pick another time, or remove that reading first.")

    def test_refusals_beside_their_fields(self, operator, node, hours):
        assert _refusal(operator.post(_readings(node), json={"value": "1"})) == (400, "meter_type_id", "Pick a meter")
        assert _refusal(_post(operator, node, hours, "")) == (400, "value", "Enter the reading")
        assert _refusal(_post(operator, node, hours, "1.25")) == (400, "value", "Enter a number with up to 1 decimal")
        assert _refusal(_post(operator, node, hours, "-1")) == (400, "value", "A counter cannot be below zero")
        assert _refusal(_post(operator, node, hours, "1", is_reset="yes")) == (
            400, "is_reset", "Meter reset must be true or false")
        assert _refusal(_post(operator, node, hours, "1", note="x" * 201)) == (
            400, "note", "Note must be at most 200 characters")
        assert _refusal(_post(operator, node, hours, "1", taken_at="24-10-2026 08:00")) == (
            400, "taken_at", "Enter the time as YYYY-MM-DD HH:MM")
        assert _refusal(_post(operator, node, hours, "1", -10)) == (400, "taken_at", "That time is in the future")

    def test_eight_days_back_is_refused_even_for_admin(self, keycloak_admin, node, hours):
        """Decision 8: a fixed 7 days for everyone, not S028's backdate_days."""
        assert _refusal(_post(keycloak_admin, node, hours, "1", 8 * 24 * 60)) == (
            400, "taken_at", "When was it read? Up to 7 days back")
        _log(keycloak_admin, node, hours, "1", 7 * 24 * 60 - 5)


class TestCounter:

    def test_lower_than_the_reading_before_is_400_with_its_code(self, operator, node, hours):
        _log(operator, node, hours, "12345.6", 60)
        res = _post(operator, node, hours, "12000", 30)
        body = res.get_json()
        when = _minutes_ago(60).strftime("%d-%m-%Y %H:%M")
        assert (res.status_code, body["field"], body["code"]) == (400, "value", "counter_lower")
        assert body["error"] == LOWER.format(when=when, shown="12,345.6 h")
        # Ticked as a reset, the same value is saved
        assert _log(operator, node, hours, "12000", 30, is_reset=True)["is_reset"] is True

    def test_a_reset_equal_to_the_reading_before_passes(self, operator, node, hours):
        """BR2-13: a replaced meter that reads 0 after a reading of 0."""
        _log(operator, node, hours, "0", 60)
        _log(operator, node, hours, "0", 30, is_reset=True)

    def test_a_reset_higher_than_the_one_before_is_refused(self, operator, node, hours):
        _log(operator, node, hours, "100", 60)
        res = _post(operator, node, hours, "200", 30, is_reset=True)
        assert _refusal(res) == (400, "is_reset", "A reset reads lower than the reading before it. Untick Meter reset.")
        assert "code" not in res.get_json()

    def test_a_back_dated_reading_must_fit_between_its_neighbours(self, operator, node, hours):
        _log(operator, node, hours, "100", 60)
        _log(operator, node, hours, "200", 20)
        _log(operator, node, hours, "150", 40)
        res = _post(operator, node, hours, "250", 30)
        when = _minutes_ago(20).strftime("%d-%m-%Y %H:%M")
        assert _refusal(res) == (400, "value", f"Higher than the later reading of {when} (200.0 h). Check the value"
                                               " and the time.")
        assert "code" not in res.get_json()

    def test_a_removed_reading_no_longer_blocks_a_lower_value(self, operator, engineer, node, hours):
        typo = _log(operator, node, hours, "99999", 60)
        assert _post(operator, node, hours, "120", 30).status_code == 400
        assert engineer.delete(_readings(node, typo)).status_code == 204
        _log(operator, node, hours, "120", 30)
        # The removed reading's minute is free again
        _log(operator, node, hours, "100", 60)

    def test_two_writers_on_one_node_serialise_and_the_second_sees_the_first(self, operator, node, hours):
        """§ 5.3: a connection holds the node lock and inserts 100; the API's lower reading waits on
        (1), then sees that row and is refused."""
        conn = get_local_db(config.DB_CONFIG)
        result = {}
        try:
            with conn.cursor() as cur:
                cur.execute("START TRANSACTION")
                cur.execute("SELECT id FROM equipment WHERE id = %s FOR UPDATE", (node["id"],))
                worker = threading.Thread(target=lambda: result.update(res=_post(operator, node, hours, "50", 10)))
                worker.start()
                time.sleep(1)
                assert worker.is_alive(), "the reading did not wait for the node lock"
                cur.execute("INSERT INTO meter_readings (equipment_id, meter_type_id, value, taken_at, created_by)"
                            " VALUES (%s, %s, 100, %s, 'other')", (node["id"], hours["id"], _minutes_ago(20)))
                cur.execute("COMMIT")
            worker.join(timeout=30)
        finally:
            conn.close()
        assert result["res"].status_code == 400
        assert result["res"].get_json()["code"] == "counter_lower"


class TestOtherKinds:

    def test_a_gauge_outside_its_limits_is_saved_and_marked(self, operator, node, oil):
        assert _log(operator, node, oil, "65", 30)["limit_state"] == "high"
        assert _log(operator, node, oil, "5", 20)["limit_state"] == "low"
        assert _log(operator, node, oil, "60", 10)["limit_state"] is None      # a limit is inside
        assert _log(operator, node, oil, "-2.5", 5)["value"] == "-2.5"          # a gauge may read below zero

    def test_an_amount_lower_than_the_one_before_is_saved(self, operator, node, shift):
        _log(operator, node, shift, "420", 60)
        reading = _log(operator, node, shift, "380", 30)
        assert (reading["value"], reading["limit_state"]) == ("380", None)
        assert _refusal(_post(operator, node, shift, "-1")) == (400, "value", "An amount cannot be below zero")
        assert _refusal(_post(operator, node, shift, "1", is_reset=True)) == (
            400, "is_reset", "Only a counter can be reset")

    def test_a_yes_no_meter_takes_the_words_and_marks_not_ok(self, operator, node, oil_ok, db_rows):
        """BR3-04: the API reads and writes the words; the table holds 1 / 0."""
        no = _log(operator, node, oil_ok, "no", 30, note="topped up")
        assert (no["value"], no["limit_state"], no["note"]) == ("no", "not_ok", "topped up")
        assert str(db_rows("SELECT value FROM meter_readings WHERE id = %s", (no["id"],))[0]["value"]) == "0.000"
        yes = _log(operator, node, oil_ok, "yes", 20)
        assert (yes["value"], yes["limit_state"]) == ("yes", None)
        assert _refusal(_post(operator, node, oil_ok, "yes", 10, is_reset=True)) == (
            400, "is_reset", "Only a counter can be reset")
        assert _refusal(_post(operator, node, oil_ok, "1", 10)) == (400, "value", "Pick Yes or No")
        assert [r["value"] for r in _history(operator, node, oil_ok)["items"]] == ["yes", "no"]

    def test_the_meters_list_carries_the_last_reading(self, operator, node, hours, oil, oil_ok):
        _log(operator, node, oil, "65", 30)
        _log(operator, node, oil, "40", 60)                  # back-dated: not the last
        _log(operator, node, oil_ok, "no", 30)
        meters = {m["meter_type"]["id"]: m for m in _ok(operator.get(f"{EQUIPMENT}/{node['id']}/meters"))}
        assert meters[oil["id"]]["last"] == {"value": "65", "taken_at": api_time(_minutes_ago(30)),
                                             "limit_state": "high"}
        assert meters[oil_ok["id"]]["last"]["value"] == "no"
        assert meters[hours["id"]]["last"] is None


class TestHistory:

    def test_paging_newest_first_with_a_back_dated_reading_on_the_boundary(self, operator, node, oil):
        for minutes in (60, 50, 40):
            _log(operator, node, oil, str(minutes), minutes)
        _log(operator, node, oil, "55", 55)                  # back-dated, between page 1 and page 2
        first = _history(operator, node, oil, per_page=2)
        second = _history(operator, node, oil, per_page=2, page=2)
        assert (first["total"], first["page"], first["per_page"]) == (4, 1, 2)
        assert [r["value"] for r in first["items"] + second["items"]] == ["40", "50", "55", "60"]

    def test_the_default_page_is_30(self, operator, node, oil):
        assert _history(operator, node, oil)["per_page"] == 30

    def test_without_a_meter_is_400(self, operator, node, oil):
        assert _refusal(operator.get(_readings(node))) == (400, "meter_type_id", "Pick a meter")

    def test_a_storekeeper_reads_and_an_outsider_gets_404(self, operator, at_unit, user_with_units, make_unit,
                                                          node, oil):
        _log(operator, node, oil, "30", 10)
        assert _history(at_unit("maint_storekeeper"), node, oil)["total"] == 1
        outsider = user_with_units("maint_engineer", [make_unit()])
        assert outsider.get(f"{_readings(node)}?meter_type_id={oil['id']}").status_code == 404

    def test_can_remove_per_role(self, operator, at_unit, admin, node, oil):
        _log(operator, node, oil, "30", 10)
        for client, expected in ((operator, False), (at_unit("maint_supervisor"), False),
                                 (at_unit("maint_engineer"), True), (at_unit("maint_manager"), True), (admin, True)):
            assert _history(client, node, oil)["items"][0]["can_remove"] is expected

    def test_can_remove_is_false_on_a_reset_with_a_later_reading_and_on_a_scrapped_node(self, operator, engineer,
                                                                                         admin, node, hours):
        _log(operator, node, hours, "100", 60)
        _log(operator, node, hours, "2", 40, is_reset=True)
        _log(operator, node, hours, "10", 20)
        assert [(r["value"], r["can_remove"]) for r in _history(engineer, node, hours)["items"]] == [
            ("10", True), ("2", False), ("100", True)]
        _ok(admin.put(f"{EQUIPMENT}/{node['id']}", json={"lifecycle": "scrapped"}))
        assert not any(r["can_remove"] for r in _history(engineer, node, hours)["items"])

    def test_removed_readings_only_for_equipment_edit_holders(self, operator, engineer, node, oil):
        wrong = _log(operator, node, oil, "300", 20)
        _log(operator, node, oil, "30", 10)
        assert engineer.delete(_readings(node, wrong)).status_code == 204
        # An operator's ask is ignored
        assert _history(operator, node, oil, include_removed=1)["total"] == 1
        shown = _history(engineer, node, oil, include_removed=1)
        removed = next(r for r in shown["items"] if r["id"] == wrong["id"])
        assert (shown["total"], removed["can_remove"], removed["removed_by"]) == (2, False, engineer._headers.get(
            "X-Test-User"))
        assert removed["removed_at"] is not None
        assert _history(engineer, node, oil)["total"] == 1


class TestRemove:

    @pytest.mark.parametrize("role", ["maint_engineer", "maint_manager", "it_admin"])
    def test_an_equipment_edit_holder_removes(self, role, operator, at_unit, admin, node, oil):
        reading = _log(operator, node, oil, "30", 10)
        client = admin if role == "it_admin" else at_unit(role)
        res = client.delete(_readings(node, reading))
        assert (res.status_code, res.data) == (204, b"")
        assert _history(operator, node, oil)["total"] == 0

    def test_the_author_and_the_supervisor_may_not(self, operator, at_unit, node, oil):
        reading = _log(operator, node, oil, "30", 10)
        for client in (operator, at_unit("maint_supervisor")):
            assert client.delete(_readings(node, reading)).status_code == 403
        assert _history(operator, node, oil)["total"] == 1

    def test_twice_is_409_and_an_unknown_reading_404(self, operator, engineer, node, oil):
        reading = _log(operator, node, oil, "30", 10)
        assert engineer.delete(_readings(node, reading)).status_code == 204
        assert _refusal(engineer.delete(_readings(node, reading))) == (409, None, "This reading was removed")
        assert engineer.delete(_readings(node, {"id": 999999999})).status_code == 404

    def test_a_reading_of_another_node_is_404(self, operator, engineer, node, oil, make_equipment, unit):
        reading = _log(operator, node, oil, "30", 10)
        other = make_equipment(unit=unit)
        assert engineer.delete(_readings(other, reading)).status_code == 404

    def test_a_reset_with_a_later_reading_is_409(self, operator, engineer, node, hours):
        _log(operator, node, hours, "100", 60)
        reset = _log(operator, node, hours, "2", 40, is_reset=True)
        later = _log(operator, node, hours, "10", 20)
        assert _refusal(engineer.delete(_readings(node, reset))) == (
            409, None, "This reading marks a meter reset. Remove the later readings first.")
        assert engineer.delete(_readings(node, later)).status_code == 204
        assert engineer.delete(_readings(node, reset)).status_code == 204

    def test_on_a_scrapped_node_is_409(self, operator, engineer, admin, node, oil):
        reading = _log(operator, node, oil, "30", 10)
        _ok(admin.put(f"{EQUIPMENT}/{node['id']}", json={"lifecycle": "scrapped"}))
        assert _refusal(engineer.delete(_readings(node, reading))) == (409, None, SCRAPPED)
