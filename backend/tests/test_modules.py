"""Version endpoint and DB status (the masters routes are tested in test_masters_api.py).

The DB status tests need the dev MariaDB container (tooling/dev/dev-db-up.bat).
"""

import pytest

import config
from local_db import LATEST_VERSION, db_status


class TestVersion:

    def test_version_is_read_from_file(self):
        # "unknown" would mean the VERSION file was not found — in the image
        # that is a missing COPY VERSION, and stale-bundle detection goes dead.
        assert config.APP_VERSION != "unknown"

    def test_version_endpoint(self, client):
        assert client.get("/api/version").get_json() == {"version": config.APP_VERSION}


class TestSettingsDbStatus:

    @pytest.mark.parametrize("role", ["maint_operator", "maint_technician", "maint_engineer"])
    def test_maintenance_floor_roles_are_forbidden(self, role_client, role):
        assert role_client(role).get("/api/settings/db-status").status_code == 403

    @pytest.mark.parametrize("role", ["maint_manager", "it_admin", "admin"])
    def test_test_db_is_reachable_and_migrated(self, role_client, role):
        res = role_client(role).get("/api/settings/db-status")
        assert res.status_code == 200
        body = res.get_json()
        assert body["error"] is None, body["error"]
        assert body["reachable"] is True
        assert body["database"] == "vel_yantra_test"
        assert body["schema_version"] == LATEST_VERSION
        assert body["schema_latest"] == LATEST_VERSION
        assert "MariaDB" in body["server_version"]
        assert body["schema_applied_at"].endswith("+05:30")


class TestDbUnreachable:

    def test_status_reports_error_instead_of_raising(self):
        cfg = dict(config.DB_CONFIG, port=1)  # nothing listens on port 1
        status = db_status(cfg)
        assert status["reachable"] is False
        assert status["schema_version"] is None
        assert status["error"]

    def test_missing_database_is_reported(self):
        cfg = dict(config.DB_CONFIG, database="vel_yantra_does_not_exist")
        status = db_status(cfg)
        assert status["reachable"] is False
        assert "vel_yantra_does_not_exist" in status["error"]
