"""The network gate, its DB-down behaviour and Settings › Network (S013 § 5.1-5.3, § 8 API).

Test requests come from 10.0.0.5 (internal) unless they send their own X-Real-IP (conftest).
"""

import logging

import pytest
from flask import g

import access_control
import config
import db_helpers
from access_control import require_network
from local_db import get_local_db
from network_core import DEFAULT_INTERNAL_NETWORKS

EXTERNAL = {"X-Real-IP": "203.0.113.7"}
SITES = "/api/masters/sites"
NETWORK = "/api/settings/network"


def _write_setting(value):
    conn = get_local_db(config.DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO app_settings (setting_key, setting_value) VALUES ('internal_networks', %s) "
                        "ON DUPLICATE KEY UPDATE setting_value = %s", (value, value))
    finally:
        conn.close()


@pytest.fixture
def networks_setting():
    """networks_setting(text) writes the stored ranges as is; the defaults are put back after."""
    yield _write_setting
    _write_setting(DEFAULT_INTERNAL_NETWORKS)
    access_control.clear_networks_cache()


@pytest.fixture
def db_down(monkeypatch):
    """Every ensure_schema reference answers "down" (S013 BR2-03): get_db() raises
    DBUnavailable, the ranges fall back, the access-log hook skips."""
    monkeypatch.setattr(db_helpers, "ensure_schema", lambda _config: "Can't connect (test)")
    monkeypatch.setattr(access_control, "ensure_schema", lambda _config: "Can't connect (test)")


class TestGate:

    def test_external_it_admin_is_refused(self, role_client):
        res = role_client("it_admin").get(SITES, headers=EXTERNAL)
        assert res.status_code == 403
        body = res.get_json()
        assert body["code"] == "network_denied" and body["ip"] == "203.0.113.7"
        assert "plant network" in body["error"]

    def test_external_it_admin_is_refused_on_me(self, role_client):
        res = role_client("it_admin").get("/api/auth/me", headers=EXTERNAL)
        assert res.status_code == 403 and res.get_json()["code"] == "network_denied"

    @pytest.mark.parametrize("role", ["maint_manager", "maint_engineer", "maint_operator", "admin"])
    def test_other_roles_pass_from_outside(self, role_client, role):
        assert role_client(role).get(SITES, headers=EXTERNAL).status_code == 200

    def test_internal_it_admin_passes(self, role_client):
        assert role_client("it_admin").get(SITES).status_code == 200

    @pytest.mark.parametrize("ip", ["10.24.3.7", "192.168.1.20", "172.20.0.1", "127.0.0.1", "::ffff:10.1.2.3"])
    def test_internal_addresses_pass(self, role_client, ip):
        assert role_client("it_admin").get(SITES, headers={"X-Real-IP": ip}).status_code == 200

    @pytest.mark.parametrize("ip", ["100.64.1.1", "8.8.8.8", "2001:db8::1"])
    def test_external_addresses_are_refused(self, role_client, ip):
        assert role_client("it_admin").get(SITES, headers={"X-Real-IP": ip}).status_code == 403

    @pytest.mark.parametrize("path", ["/api/health", "/api/version", "/api/auth/config"])
    def test_public_paths_from_outside(self, client, path):
        assert client.get(path, headers=EXTERNAL).status_code == 200

    def test_a_missing_address_is_external(self, role_client):
        res = role_client("it_admin").get(SITES, headers={"X-Real-IP": ""})
        assert res.status_code == 403 and res.get_json()["ip"] == ""

    def test_forwarded_for_is_never_read(self, role_client):
        res = role_client("it_admin").get(SITES, headers={**EXTERNAL, "X-Forwarded-For": "10.24.0.5"})
        assert res.status_code == 403

    def test_no_token_from_outside_is_401_not_403(self, client):
        assert client.get(SITES, headers=EXTERNAL).status_code == 401

    def test_dev_bypass_passes(self, app):
        handler = require_network(dev_bypass=True)
        with app.test_request_context(SITES, headers=EXTERNAL):
            g.user = {"username": "dev", "roles": ["it_admin"]}
            assert handler() is None

    def test_the_handler_refuses_without_the_bypass(self, app):
        handler = require_network(dev_bypass=False)
        with app.test_request_context(SITES, headers=EXTERNAL):
            g.user = {"username": "x", "roles": ["it_admin"]}
            assert handler()[1] == 403

    def test_me_reports_the_network(self, role_client):
        body = role_client("maint_engineer").get("/api/auth/me", headers=EXTERNAL).get_json()
        assert body["network"] == {"ip": "203.0.113.7", "internal": False}
        body = role_client("it_admin").get("/api/auth/me").get_json()
        assert body["network"] == {"ip": "10.0.0.5", "internal": True}

    def test_refusal_is_logged(self, role_client, caplog):
        with caplog.at_level(logging.WARNING):
            role_client("it_admin").get(SITES, headers=EXTERNAL)
        assert any("Network gate" in r.getMessage() and "203.0.113.7" in r.getMessage() for r in caplog.records)

    def test_no_test_user_factory_is_401(self, app, monkeypatch):
        """S013 BR2-05: X-Test-Role without a factory fails closed."""
        monkeypatch.delitem(app.config, "TEST_USER_FACTORY")
        assert app.test_client().get(SITES, headers={"X-Test-Role": "it_admin"}).status_code == 401


class TestDatabaseDown:
    """S013 BR1-01: the gate decides without the database; the hook neither slows nor breaks."""

    def test_internal_it_admin_still_reaches_me(self, role_client, db_down):
        res = role_client("it_admin").get("/api/auth/me")
        assert res.status_code == 200
        assert res.get_json()["db_unavailable"] is True
        assert res.get_json()["network"]["internal"] is True

    def test_external_it_admin_is_refused(self, role_client, db_down):
        assert role_client("it_admin").get("/api/auth/me", headers=EXTERNAL).status_code == 403

    def test_ranges_fall_back_to_the_cache(self, role_client, networks_setting, monkeypatch):
        networks_setting("192.168.50.0/24")
        assert role_client("it_admin").get(SITES, headers={"X-Real-IP": "192.168.50.9"}).status_code == 200
        # The cache has expired, and the database is gone: the last list read still holds
        monkeypatch.setattr(access_control, "_networks_read_at", -10_000.0)
        monkeypatch.setattr(db_helpers, "ensure_schema", lambda _config: "down")
        res = role_client("it_admin").get("/api/auth/me", headers={"X-Real-IP": "192.168.50.9"})
        assert res.status_code == 200
        res = role_client("it_admin").get("/api/auth/me", headers={"X-Real-IP": "10.24.0.5"})
        assert res.status_code == 403   # not in the cached list

    def test_ranges_fall_back_to_the_defaults(self, role_client, db_down):
        assert role_client("it_admin").get("/api/auth/me", headers={"X-Real-IP": "10.24.0.5"}).status_code == 200


class TestNetworkSetting:

    def test_read(self, role_client, networks_setting):
        networks_setting(DEFAULT_INTERNAL_NETWORKS)
        body = role_client("it_admin").get(NETWORK).get_json()
        assert body == {"networks": DEFAULT_INTERNAL_NETWORKS.split(","), "your_ip": "10.0.0.5",
                        "your_ip_internal": True}

    def test_manager_reads_engineer_does_not(self, role_client):
        assert role_client("maint_manager").get(NETWORK).status_code == 200
        assert role_client("maint_engineer").get(NETWORK).status_code == 403

    def test_manager_cannot_save(self, role_client):
        assert role_client("maint_manager").put(NETWORK, json={"networks": "10.0.0.0/8"}).status_code == 403

    def test_save_normalises_and_applies_at_once(self, role_client, networks_setting, db_rows, caplog):
        networks_setting(DEFAULT_INTERNAL_NETWORKS)
        with caplog.at_level(logging.INFO):
            res = role_client("it_admin").put(NETWORK, json={"networks": " 10.0.0.5/8 ,\n172.31.4.0/22\n"})
        assert res.status_code == 200, res.get_json()
        assert res.get_json()["networks"] == ["10.0.0.0/8", "172.31.4.0/22"]
        stored = db_rows("SELECT setting_value FROM app_settings WHERE setting_key = 'internal_networks'")
        assert stored[0]["setting_value"] == "10.0.0.0/8,172.31.4.0/22"
        assert any("internal_networks changed by test_it_admin" in r.getMessage()
                   and DEFAULT_INTERNAL_NETWORKS in r.getMessage() for r in caplog.records)
        # This process's cache was cleared: 192.168.x is external now
        assert role_client("it_admin").get(SITES, headers={"X-Real-IP": "192.168.1.5"}).status_code == 403

    def test_host_bits_are_dropped(self, role_client, networks_setting):
        networks_setting(DEFAULT_INTERNAL_NETWORKS)
        res = role_client("it_admin").put(NETWORK, json={"networks": "10.0.0.5/16"})
        assert res.get_json()["networks"] == ["10.0.0.0/16"]

    def test_a_bad_range_is_named(self, role_client, networks_setting):
        networks_setting(DEFAULT_INTERNAL_NETWORKS)
        res = role_client("it_admin").put(NETWORK, json={"networks": "10.0.0.0/8, 10.0.0.0/33"})
        assert res.status_code == 400
        assert res.get_json()["field"] == "networks" and "10.0.0.0/33" in res.get_json()["error"]

    @pytest.mark.parametrize("body", [{"networks": ""}, {"networks": " ,\n"}])
    def test_empty_is_refused(self, role_client, networks_setting, body):
        networks_setting(DEFAULT_INTERNAL_NETWORKS)
        res = role_client("it_admin").put(NETWORK, json=body)
        assert res.status_code == 400 and res.get_json()["error"] == "At least one range is needed"

    @pytest.mark.parametrize("body", [{}, {"networks": ["10.0.0.0/8"]}, {"networks": None}])
    def test_not_text_is_refused(self, role_client, body):
        assert role_client("it_admin").put(NETWORK, json=body).status_code == 400

    def test_a_list_that_blocks_the_saver_is_refused(self, role_client, networks_setting, db_rows):
        networks_setting(DEFAULT_INTERNAL_NETWORKS)
        res = role_client("it_admin").put(NETWORK, json={"networks": "192.168.0.0/16"})
        assert res.status_code == 400
        assert "This would block your own address (10.0.0.5)" in res.get_json()["error"]
        stored = db_rows("SELECT setting_value FROM app_settings WHERE setting_key = 'internal_networks'")
        assert stored[0]["setting_value"] == DEFAULT_INTERNAL_NETWORKS

    def test_admin_may_save_a_list_that_blocks_them(self, role_client, networks_setting):
        networks_setting(DEFAULT_INTERNAL_NETWORKS)
        res = role_client("admin").put(NETWORK, json={"networks": "192.168.0.0/16"})
        assert res.status_code == 200 and res.get_json()["your_ip_internal"] is False

    def test_a_corrupt_stored_value_gives_the_defaults(self, role_client, networks_setting, caplog):
        networks_setting("10.0.0.0/8, not a range")
        with caplog.at_level(logging.WARNING):
            body = role_client("it_admin").get(NETWORK).get_json()
        assert body["networks"] == DEFAULT_INTERNAL_NETWORKS.split(",")
        assert any("internal_networks" in r.getMessage() for r in caplog.records)
        # The gate uses the defaults too
        assert role_client("it_admin").get(SITES, headers={"X-Real-IP": "192.168.9.9"}).status_code == 200
