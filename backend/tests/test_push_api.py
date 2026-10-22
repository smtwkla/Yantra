"""My notifications' API — /api/push (S021 § 5.5, § 6, § 8 API and tasks).  Devices are seeded
through the real subscribe route; the push services are never reached (nothing here runs the
worker)."""

import json
import logging
import uuid

import pytest

from push_core import endpoint_hash

PUSH = "/api/push"
ANDROID_CHROME = ("Mozilla/5.0 (Linux; Android 14; SM-A546E) AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/130.0.0.0 Mobile Safari/537.36")


def new_endpoint():
    return f"https://fcm.googleapis.com/fcm/send/test-{uuid.uuid4().hex}"


def subscription(endpoint=None):
    return {"endpoint": endpoint or new_endpoint(), "keys": {"p256dh": "BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_0QTpQ",
                                                            "auth": "tBHItJI5svbpez7KI4CCXg"}}


def turn_on(client, body=None):
    body = body or subscription()
    res = client.post(f"{PUSH}/subscriptions", json=body, headers={"User-Agent": ANDROID_CHROME})
    assert res.status_code == 201, res.get_json()
    return body, res.get_json()


@pytest.fixture
def site(make_site):
    return make_site()


@pytest.fixture
def engineer_in_team(user_at_sites, site):
    """(client, person): an engineer at the site, all units, with a login and a Team record."""
    return user_at_sites([(site, "maint_engineer", "all")])


@pytest.fixture
def other_in_team(user_at_sites, site):
    return user_at_sites([(site, "maint_technician", "all")])


class TestConfig:

    def test_push_on_with_the_public_key_and_what_you_get(self, engineer_in_team, site):
        client, _person = engineer_in_team
        body = client.get(f"{PUSH}/config").get_json()
        assert body["enabled"] is True
        assert len(body["public_key"]) == 87
        assert body["you_get"] == [f"Breakdowns and defects at {site['code']}, escalations", "Jobs assigned to you"]

    def test_push_off_without_keys(self, engineer_in_team, push_off):
        client, _person = engineer_in_team
        body = client.get(f"{PUSH}/config").get_json()
        assert body["enabled"] is False and body["public_key"] == ""

    def test_no_team_record_gets_nothing(self, role_client):
        body = role_client("maint_engineer", "push_nobody").get(f"{PUSH}/config").get_json()
        assert body["you_get"] == []

    def test_a_login_with_no_role_is_forbidden(self, role_client):
        assert role_client("maintenance_team", "push_login_only").get(f"{PUSH}/config").status_code == 403


class TestSubscribe:

    def test_subscribe_and_list_mine(self, engineer_in_team, other_in_team):
        client, _person = engineer_in_team
        body, device = turn_on(client)
        assert device["label"] == "Android · Chrome" and device["this_device"] is True
        assert device["last_sent_at"] is None and device["last_error"] is None
        listed = client.get(f"{PUSH}/subscriptions?endpoint_hash={endpoint_hash(body['endpoint'])}").get_json()
        assert listed["total"] == 1 and listed["items"][0]["id"] == device["id"]
        assert listed["items"][0]["this_device"] is True
        assert "endpoint" not in listed["items"][0] and "p256dh" not in listed["items"][0]
        other, _ = other_in_team
        assert other.get(f"{PUSH}/subscriptions").get_json()["total"] == 0

    @pytest.mark.parametrize("query", ["", "?endpoint_hash=abc", "?endpoint_hash=" + "A" * 64])
    def test_a_bad_hash_marks_no_row(self, engineer_in_team, query):
        client, _person = engineer_in_team
        turn_on(client)
        res = client.get(f"{PUSH}/subscriptions{query}")
        assert res.status_code == 200
        assert [item["this_device"] for item in res.get_json()["items"]] == [False]

    def test_resubscribe_moves_the_device(self, engineer_in_team, other_in_team, db_rows):
        client, _person = engineer_in_team
        body, device = turn_on(client)
        db_rows("UPDATE push_subscriptions SET last_sent_at = NOW(), last_error = 'x' WHERE id = %s", (device["id"],))
        other, other_person = other_in_team
        _, moved = turn_on(other, {**body, "keys": {"p256dh": "BNewKey", "auth": "newAuth"}})
        assert moved["id"] == device["id"]
        assert moved["last_sent_at"] is None and moved["last_error"] is None
        row = db_rows("SELECT person_id, p256dh, auth FROM push_subscriptions WHERE id = %s", (device["id"],))[0]
        assert row == {"person_id": other_person["id"], "p256dh": "BNewKey", "auth": "newAuth"}
        assert client.get(f"{PUSH}/subscriptions").get_json()["total"] == 0

    def test_no_team_record_is_409(self, role_client):
        res = role_client("maint_engineer", "push_nobody").post(f"{PUSH}/subscriptions", json=subscription())
        assert res.status_code == 409
        assert res.get_json()["error"] == "You are not in Team. Ask IT admin to add you."

    def test_a_bad_address_is_400_and_the_log_names_the_host_only(self, engineer_in_team, caplog, db_rows):
        client, _person = engineer_in_team
        caplog.set_level(logging.WARNING, logger="push")
        res = client.post(f"{PUSH}/subscriptions", json=subscription("https://push.example.org/secret-device-token"))
        assert res.status_code == 400
        assert res.get_json()["error"] == ("This browser cannot get notifications. Use Chrome on Android, or open "
                                           "Yantra from the Home Screen on an iPhone.")
        logged = " ".join(r.getMessage() for r in caplog.records)
        assert "push.example.org" in logged and "secret-device-token" not in logged

    @pytest.mark.parametrize("endpoint", [
        "https://10.24.0.10\\.fcm.googleapis.com/",            # CR1-01: requests would post to 10.24.0.10
        "https://evil.example%2f.fcm.googleapis.com/x",
        "https://fcm.googleapis.com@evil.example/x",
    ])
    def test_an_address_the_parsers_read_differently_is_400_and_not_stored(self, engineer_in_team, endpoint,
                                                                            db_rows):
        client, _person = engineer_in_team
        res = client.post(f"{PUSH}/subscriptions", json=subscription(endpoint))
        assert res.status_code == 400
        assert res.get_json()["error"].startswith("This browser cannot get notifications.")
        assert db_rows("SELECT id FROM push_subscriptions WHERE endpoint_hash = %s",
                       (endpoint_hash(endpoint),)) == ()

    def test_a_body_without_keys_is_400(self, engineer_in_team):
        client, _person = engineer_in_team
        res = client.post(f"{PUSH}/subscriptions", json={"endpoint": new_endpoint()})
        assert res.status_code == 400


class TestRemove:

    def test_remove_mine_and_not_someone_elses(self, engineer_in_team, other_in_team):
        client, _person = engineer_in_team
        _, device = turn_on(client)
        other, _ = other_in_team
        assert other.delete(f"{PUSH}/subscriptions/{device['id']}").status_code == 404
        assert client.delete(f"{PUSH}/subscriptions/{device['id']}").status_code == 204
        assert client.get(f"{PUSH}/subscriptions").get_json()["total"] == 0
        assert client.delete(f"{PUSH}/subscriptions/{device['id']}").status_code == 404

    def test_remove_by_endpoint_whoever_owns_it(self, engineer_in_team, role_client, db_rows):
        client, _person = engineer_in_team
        body, device = turn_on(client)
        # Someone else signs out on the handed-over phone (BR3-03): a login with no Team record at all
        res = role_client("maint_operator", "push_next_user").post(f"{PUSH}/subscriptions/remove",
                                                                   json={"endpoint": body["endpoint"]})
        assert res.status_code == 204
        assert db_rows("SELECT id FROM push_subscriptions WHERE id = %s", (device["id"],)) == ()

    def test_remove_by_an_unknown_endpoint_is_204(self, engineer_in_team):
        client, _person = engineer_in_team
        assert client.post(f"{PUSH}/subscriptions/remove", json={"endpoint": new_endpoint()}).status_code == 204

    def test_remove_by_endpoint_needs_one(self, engineer_in_team):
        client, _person = engineer_in_team
        assert client.post(f"{PUSH}/subscriptions/remove", json={}).status_code == 400


def _test_sends(db_rows, subscription_id):
    rows = db_rows("SELECT payload, max_attempts FROM task_queue WHERE task_type = 'push_send'"
                   " AND JSON_EXTRACT(payload, '$.subscription_id') = %s", (subscription_id,))
    return [(json.loads(r["payload"]), r["max_attempts"]) for r in rows]


class TestSendTest:

    def test_to_every_device_of_mine(self, engineer_in_team, db_rows):
        client, _person = engineer_in_team
        _, first = turn_on(client)
        _, second = turn_on(client)
        res = client.post(f"{PUSH}/test")
        assert res.status_code == 200 and res.get_json() == {"devices": 2}
        for device in (first, second):
            ((payload, attempts),) = _test_sends(db_rows, device["id"])
            assert payload == {"subscription_id": device["id"], "title": "Yantra test",
                               "body": "Notifications work on this device.", "path": "/notifications",
                               "tag": "test", "urgency": "high", "silent": False, "ttl": 300}
            assert attempts == 3

    def test_none_turned_on_is_409(self, engineer_in_team):
        client, _person = engineer_in_team
        res = client.post(f"{PUSH}/test")
        assert res.status_code == 409 and res.get_json()["error"] == "Turn notifications on first."

    def test_push_off_is_409(self, engineer_in_team, push_off):
        client, _person = engineer_in_team
        res = client.post(f"{PUSH}/test")
        assert res.status_code == 409
        assert res.get_json()["error"] == "Notifications are not set up on this server yet. Ask IT admin."
