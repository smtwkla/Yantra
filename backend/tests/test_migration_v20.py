"""v20, the squashed schema (S025 § 1.1, § 8), in its own database vel_yantra_upgrade, dropped and
created by these tests (tooling/run-backend-tests.bat grants it on an existing container).

- equivalence: the schema v20 builds on an empty database is the one v1–v13 built;
- production path: a v0.1.3 database (v1–v5) with its masters filled is refused while it holds
  the v5 equipment tables, unchanged; after the user's two drops it reaches today's schema with
  its masters intact and the legacy unit-access rows moved into Team;
- dev path: a v13 database gets v20 recorded with nothing changed;
- re-run: v20 twice changes nothing.

The old migrations run from the frozen fixture (tests/fixtures/migrations_v13.py) by replacing
local_db._MIGRATIONS; the engine itself is unchanged.  Needs the dev MariaDB container.
"""

import pymysql
import pytest

import config
import local_db
from local_db import MigrationBlocked, describe_error, get_local_db, init_db
from tests.fixtures.migrations_v13 import MIGRATIONS_V13

UPGRADE_DB = "vel_yantra_upgrade"
UPGRADE_CONFIG = {**config.DB_CONFIG, "database": UPGRADE_DB}
# v20 alone: later versions (v21, S019) are tested on their own (S019 BS1-04)
V20 = [m for m in local_db._MIGRATIONS if m[0] == 20]
V0_1_3 = MIGRATIONS_V13[:5]   # byte-identical to release v0.1.3's (the fixture's docstring)

BOTH_OLD = "Drop the old equipment and equipment_events tables first (they must be empty) — S025 § 5.1"


def _recreate():
    """An empty upgrade database, as tooling/e2e/e2e_backend.py makes the e2e one."""
    conn = pymysql.connect(host=UPGRADE_CONFIG["host"], port=UPGRADE_CONFIG["port"], user=UPGRADE_CONFIG["user"],
                           password=UPGRADE_CONFIG["password"], autocommit=True)
    try:
        with conn.cursor() as cur:
            cur.execute(f"DROP DATABASE IF EXISTS `{UPGRADE_DB}`")
            cur.execute(f"CREATE DATABASE `{UPGRADE_DB}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    finally:
        conn.close()


def _run(sql, params=()):
    conn = get_local_db(UPGRADE_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()
    finally:
        conn.close()


def _migrate(migrations):
    """init_db on the upgrade database with ``migrations`` as the migration list."""
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(local_db, "_MIGRATIONS", migrations)
        init_db(UPGRADE_CONFIG)


def _rows(sql):
    return sorted(tuple(r.values()) for r in _run(sql))


def _schema():
    """Everything a migration defines, from information_schema, for this database only."""
    return {
        "tables": _rows("SELECT TABLE_NAME, ENGINE, TABLE_COLLATION FROM information_schema.TABLES"
                        " WHERE TABLE_SCHEMA = DATABASE()"),
        "columns": _rows("SELECT TABLE_NAME, ORDINAL_POSITION, COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT,"
                         " EXTRA, CHARACTER_SET_NAME, COLLATION_NAME FROM information_schema.COLUMNS"
                         " WHERE TABLE_SCHEMA = DATABASE()"),
        # Including the indexes MariaDB creates for foreign keys
        "indexes": _rows("SELECT TABLE_NAME, INDEX_NAME, NON_UNIQUE, SEQ_IN_INDEX, COLUMN_NAME"
                         " FROM information_schema.STATISTICS WHERE TABLE_SCHEMA = DATABASE()"),
        "foreign_keys": _rows("SELECT CONSTRAINT_NAME, TABLE_NAME, REFERENCED_TABLE_NAME, DELETE_RULE, UPDATE_RULE"
                              " FROM information_schema.REFERENTIAL_CONSTRAINTS WHERE CONSTRAINT_SCHEMA = DATABASE()"),
        "foreign_key_columns": _rows(
            "SELECT CONSTRAINT_NAME, TABLE_NAME, ORDINAL_POSITION, COLUMN_NAME, REFERENCED_TABLE_NAME,"
            " REFERENCED_COLUMN_NAME FROM information_schema.KEY_COLUMN_USAGE"
            " WHERE TABLE_SCHEMA = DATABASE() AND REFERENCED_TABLE_NAME IS NOT NULL"),
        "checks": _rows("SELECT TABLE_NAME, CONSTRAINT_NAME, CHECK_CLAUSE FROM information_schema.CHECK_CONSTRAINTS"
                        " WHERE CONSTRAINT_SCHEMA = DATABASE()"),
    }


def _versions():
    return [r["version"] for r in _run("SELECT version FROM db_version ORDER BY version")]


@pytest.fixture(scope="module")
def reference():
    """Today's schema as v1–v13 built it."""
    _recreate()
    _migrate(MIGRATIONS_V13)
    return _schema()


def test_v20_builds_the_schema_v1_to_v13_built(reference):
    _recreate()
    _migrate(V20)
    built = _schema()
    assert len(built["tables"]) == len(reference["tables"]) == 27
    for part in reference:
        assert built[part] == reference[part], part
    assert _versions() == [20]
    # The data statements ran: the settings and the failure-code seed
    assert {r["setting_key"] for r in _run("SELECT setting_key FROM app_settings")} == {
        "upload_max_mb", "internal_networks"}
    counts = [_run(f"SELECT COUNT(*) AS n FROM {t} WHERE created_by = 'migration-v11'")[0]["n"]
              for t in ("failure_modes", "failure_causes", "maintenance_actions")]
    assert counts == [14, 15, 12]


# --- Production's path: v0.1.3 (schema v5), masters filled, no equipment ------------------

_MASTERS = ("sites", "units", "equipment_classes", "equipment_types", "user_units", "serial_counters")


def _fill_v013_masters():
    """Masters as v0.1.3's screens wrote them; no equipment rows (U1, 21-10-2026)."""
    _run("INSERT INTO sites (code, name, active, is_default, created_by) VALUES ('SMTW', 'SMTW plant', 1, 1, 'kla')")
    _run("INSERT INTO sites (code, name, created_by) VALUES ('VEL', 'Vel plant', 'kla')")
    site = _run("SELECT id FROM sites WHERE code = 'SMTW'")[0]["id"]
    for code in ("FWMILL", "MCC1"):
        _run("INSERT INTO units (site_id, code, name, created_by) VALUES (%s, %s, %s, 'kla')", (site, code, code))
    _run("INSERT INTO equipment_classes (code, name, created_by) VALUES ('HP', 'Hydraulic press', 'kla')")
    cls = _run("SELECT id FROM equipment_classes WHERE code = 'HP'")[0]["id"]
    _run("INSERT INTO equipment_types (class_id, name, created_by) VALUES (%s, 'Four-column', 'kla')", (cls,))
    units = [r["id"] for r in _run("SELECT id FROM units ORDER BY id")]
    for username, unit in (("ravi", units[0]), ("ravi", units[1]), ("selvi", units[1])):
        _run("INSERT INTO user_units (username, unit_id, granted_at, granted_by)"
             " VALUES (%s, %s, '2026-10-01 09:00:00', 'it_old')", (username, unit))
    _run("INSERT INTO app_settings (setting_key, setting_value) VALUES ('label_base_url', 'https://example.test')")


def _masters():
    return {table: _rows(f"SELECT * FROM {table}") for table in (*_MASTERS, "app_settings")}


def test_production_is_refused_unchanged_until_the_two_tables_are_dropped(reference):
    _recreate()
    _migrate(V0_1_3)
    _fill_v013_masters()
    before_schema, before_masters = _schema(), _masters()

    with pytest.raises(MigrationBlocked) as refused:
        _migrate(V20)
    assert str(refused.value) == BOTH_OLD
    # Settings › Database shows ensure_schema's _last_error, which is this text
    assert describe_error(refused.value) == BOTH_OLD
    assert _versions() == [1, 2, 3, 4, 5]
    assert _schema() == before_schema
    assert _masters() == before_masters

    # The user's § 5.1 steps 2-3 (events first: they reference equipment)
    assert _run("SELECT COUNT(*) AS n FROM equipment")[0]["n"] == 0
    _run("DROP TABLE equipment_events")
    _run("DROP TABLE equipment")
    _migrate(V20)

    assert _versions() == [1, 2, 3, 4, 5, 20]
    assert _schema() == reference
    after = _masters()
    for table in _MASTERS:
        assert after[table] == before_masters[table], table
    # The two defaults are added; a stored setting is kept
    assert {r["setting_key"] for r in _run("SELECT setting_key FROM app_settings")} == {
        "label_base_url", "upload_max_mb", "internal_networks"}
    assert _run("SELECT setting_value FROM app_settings WHERE setting_key = 'label_base_url'")[0][
        "setting_value"] == "https://example.test"
    # user_units moved into Team as v8 would have: a person per username, no membership
    people = _run("SELECT name, username, employment, active, created_by FROM people ORDER BY username")
    assert people == [
        {"name": "ravi", "username": "ravi", "employment": "direct", "active": 1, "created_by": "migration-v8"},
        {"name": "selvi", "username": "selvi", "employment": "direct", "active": 1, "created_by": "migration-v8"},
    ]
    moved = _rows("SELECT p.username, u.code, pu.granted_by FROM person_units pu JOIN people p ON p.id = pu.person_id"
                  " JOIN units u ON u.id = pu.unit_id")
    assert moved == [("ravi", "FWMILL", "it_old"), ("ravi", "MCC1", "it_old"), ("selvi", "MCC1", "it_old")]
    assert _run("SELECT COUNT(*) AS n FROM memberships")[0]["n"] == 0


def test_one_old_table_is_named_alone():
    _recreate()
    _migrate(V0_1_3)
    _run("DROP TABLE equipment_events")
    with pytest.raises(MigrationBlocked) as refused:
        _migrate(V20)
    assert str(refused.value) == "Drop the old equipment table first (it must be empty) — S025 § 5.1"


# --- Dev and test databases (at v13), and a re-run ---------------------------------------

def _data():
    """The rows a v13 database holds, for 'nothing changed'."""
    return {table: _rows(f"SELECT * FROM {table}")
            for table in ("app_settings", "sites", "people", "person_units", "failure_modes", "failure_causes",
                          "maintenance_actions")}


def test_a_v13_database_records_v20_and_changes_nothing(reference):
    _recreate()
    _migrate(MIGRATIONS_V13)
    _run("INSERT INTO sites (code, name, created_by) VALUES ('SMTW', 'SMTW plant', 'kla')")
    _run("UPDATE failure_modes SET label = 'Noisy', active = 0 WHERE code = 'NOI'")
    _run("UPDATE app_settings SET setting_value = '10.24.0.0/16' WHERE setting_key = 'internal_networks'")
    before_data = _data()

    _migrate(V20)
    assert _versions() == [*range(1, 14), 20]
    assert _schema() == reference
    assert _data() == before_data

    # Re-run: v20 twice is a no-op
    for _ in range(2):
        _run("DELETE FROM db_version WHERE version = 20")
        _migrate(V20)
    assert _versions() == [*range(1, 14), 20]
    assert _schema() == reference
    assert _data() == before_data
