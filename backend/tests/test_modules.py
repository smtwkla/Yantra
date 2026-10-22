"""Version endpoint, DB status and the migration lock (the masters routes are tested in
test_masters_api.py).

The DB status tests need the dev MariaDB container (tooling/dev/dev-db-up.bat).
"""

import pytest

import config
import local_db
from local_db import LATEST_VERSION, LOCK_MIGRATIONS, db_status, get_local_db, init_db, named_lock
from tests.db_names import TEST_DB


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
        assert body["database"] == TEST_DB
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


class TestMigrationLock:
    """GET_LOCK names are server-wide: the migration lock carries the database's name, so a
    migration of one database never waits for another's (parallel test workers, or two
    databases on one production server)."""

    def test_the_name_carries_the_database(self):
        assert named_lock(LOCK_MIGRATIONS, "vel_yantra_master") == "yantra_migrations:vel_yantra_master"

    def test_a_name_over_the_mariadb_limit_is_refused(self):
        assert len(named_lock(LOCK_MIGRATIONS, "x" * (64 - len(LOCK_MIGRATIONS) - 1))) == 64
        with pytest.raises(ValueError, match="65 characters"):
            named_lock(LOCK_MIGRATIONS, "x" * (64 - len(LOCK_MIGRATIONS)))

    def test_init_db_holds_the_lock_of_its_database(self, monkeypatch):
        held = []
        read_versions = local_db._get_applied_versions

        def spy(cur):
            cur.execute("SELECT IS_USED_LOCK(%s) = CONNECTION_ID() AS mine", (named_lock(LOCK_MIGRATIONS, TEST_DB),))
            held.append(cur.fetchone()["mine"])
            return read_versions(cur)
        monkeypatch.setattr(local_db, "_get_applied_versions", spy)
        init_db(config.DB_CONFIG)
        assert held == [1]
        # ...and lets it go afterwards
        assert lock_is_free(named_lock(LOCK_MIGRATIONS, TEST_DB))


def lock_is_free(lock):
    conn = get_local_db(config.DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT IS_FREE_LOCK(%s) AS free", (lock,))
            return cur.fetchone()["free"] == 1
    finally:
        conn.close()
