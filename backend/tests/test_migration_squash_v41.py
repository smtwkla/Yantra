"""The squashed v41 (S088 § 8.1), in the upgrade database UPGRADE_DB (one per test run and worker,
tests/db_names.py), dropped and created by these tests.

- equivalence: on an empty database the squashed v41 builds the schema and the seed rows that
  v20–v41 built (the frozen fixture tests/fixtures/migrations_v41.py);
- production's path: a database built by v20–v41, with rows, skips the squashed v41 and gets
  v50, every row kept, the same schema as a fresh database;
- the precondition: a database at v40, or at v13, is refused with nothing applied;
- re-runs: a half-applied v41 completes; a re-run keeps edited rows and restores a missing setting.

The fixture is applied in one call on an empty database (its docstring says why).  Needs the dev
MariaDB container.
"""

import pytest

import local_db
from local_db import MigrationBlocked, describe_error, get_local_db
from tests.fixtures.migrations_v41 import MIGRATIONS_V41
from tests.migration_helpers import SQUASHED, UPGRADE_CONFIG, _migrate, _recreate, _run, _schema, _versions
from tests.test_migration_v22 import _fill_one_ticket
from tests.test_migration_v36 import _one_improvement
from tests.test_migration_v38 import _add_action
from tests.test_migration_v41 import _add_lesson

OLD = MIGRATIONS_V41
CURRENT = local_db._MIGRATIONS
V41_TABLES = 46


def _refusal(version):
    return (f"This database is at schema v{version}, older than v41, and this release cannot update it. "
            "A dev or test database: drop it and start the app again. "
            "A restored production database: deploy release v0.1.14 first, which brings it to v41. — S088 § 5.2")


def _tables():
    return [r["TABLE_NAME"] for r in _run("SELECT TABLE_NAME FROM information_schema.TABLES"
                                          " WHERE TABLE_SCHEMA = DATABASE() ORDER BY TABLE_NAME")]


def _columns(timestamps=False):
    """Every table's columns but db_version's, in order -> {table: [column]}; without the ones
    CURRENT_TIMESTAMP fills (they differ between two builds) unless ``timestamps``."""
    columns = {}
    for r in _run("SELECT TABLE_NAME, COLUMN_NAME, COLUMN_DEFAULT FROM information_schema.COLUMNS"
                  " WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME <> 'db_version'"
                  " ORDER BY TABLE_NAME, ORDINAL_POSITION"):
        if timestamps or r["COLUMN_DEFAULT"] != "current_timestamp()":
            columns.setdefault(r["TABLE_NAME"], []).append(r["COLUMN_NAME"])
    return columns


def _all_rows(columns=None):
    """Every table's rows but db_version's, ids included -> {table: sorted rows}.  ``columns`` (as
    _columns returns) reads only those tables and columns, so rows read before a later version
    added a column compare with rows read after.  One connection: a connection per table makes the
    module several times slower."""
    columns = columns or _columns()
    conn = get_local_db(UPGRADE_CONFIG)
    try:
        with conn.cursor() as cur:
            rows = {}
            for table, names in columns.items():
                cur.execute(f"SELECT {', '.join(f'`{n}`' for n in names)} FROM `{table}`")
                rows[table] = sorted(tuple(r.values()) for r in cur.fetchall())
            return rows
    finally:
        conn.close()


@pytest.fixture(scope="module")
def reference():
    """The schema and the rows v20–v41 built on an empty database."""
    _recreate()
    _migrate(OLD)
    return _schema(), _all_rows()


def test_v41_builds_what_v20_to_v41_built(reference):
    schema, rows = reference
    _recreate()
    _migrate(SQUASHED)
    built = _schema()
    assert len(built["tables"]) == len(schema["tables"]) == V41_TABLES
    for part in schema:
        assert built[part] == schema[part], part
    assert _all_rows() == rows
    # The seeds of § 4 item 2, ids included in the comparison above
    seeded = {table: len(r) for table, r in rows.items() if r}
    assert seeded == {"app_settings": 5, "failure_modes": 14, "failure_causes": 15, "maintenance_actions": 12,
                      "meter_types": 8, "property_definitions": 23, "property_options": 20}
    assert _versions() == [41]


def test_production_s_v41_gets_v50():
    """Production's path: v41 recorded through v20–v41, so the squashed v41 never runs there; v50 follows."""
    _recreate()
    _migrate(OLD)
    _fill_one_ticket()
    action_id = _add_action(_one_improvement())
    _add_lesson("OPL-001", action_id)
    old_description = _run("SELECT description FROM db_version WHERE version = 41")[0]["description"]
    columns = _columns(timestamps=True)
    before = _all_rows(columns=columns)

    _migrate(CURRENT)
    assert _versions() == [*range(20, 42), 50]
    assert _run("SELECT description FROM db_version WHERE version = 41")[0]["description"] == old_description
    assert old_description == "One-point lessons and their photos (S075)"
    assert _all_rows(columns=columns) == before
    assert before["procedures"] and before["improvement_actions"] and before["tickets"]
    upgraded = _schema()

    _recreate()
    _migrate(CURRENT)
    assert _schema() == upgraded


def test_a_database_below_v41_is_refused_unchanged():
    _recreate()
    _migrate([m for m in OLD if m[0] < 41])
    versions, schema = _versions(), _schema()
    assert versions == [*range(20, 41)]

    with pytest.raises(MigrationBlocked) as refused:
        _migrate(CURRENT)
    assert str(refused.value) == _refusal(40)
    # Settings › Database shows ensure_schema's _last_error, which is this text
    assert describe_error(refused.value) == _refusal(40)
    assert _versions() == versions
    assert _schema() == schema


def test_a_v13_database_is_refused():
    _recreate()
    _run("CREATE TABLE db_version (version INT PRIMARY KEY, description VARCHAR(255),"
         " applied_at DATETIME DEFAULT CURRENT_TIMESTAMP)")
    for version in range(1, 14):
        _run("INSERT INTO db_version (version, description) VALUES (%s, 'old')", (version,))

    with pytest.raises(MigrationBlocked) as refused:
        _migrate(CURRENT)
    assert str(refused.value) == _refusal(13)
    assert _versions() == list(range(1, 14))
    assert _tables() == ["db_version"]


def test_a_half_applied_v41_re_runs(reference):
    schema, rows = reference
    version, description, statements = SQUASHED[0]
    _recreate()
    # The first half of v41, then its version row deleted: a real half-applied run records nothing
    _migrate([(version, description, statements[:len(statements) // 2])])
    _run("DELETE FROM db_version WHERE version = 41")
    assert 0 < len(_tables()) < V41_TABLES

    _migrate(SQUASHED)
    assert _schema() == schema
    assert _all_rows() == rows
    assert _versions() == [41]


def test_a_rerun_keeps_edits_and_restores_a_missing_setting():
    _recreate()
    _migrate(SQUASHED)
    _run("UPDATE failure_modes SET label = 'Noisy', active = 0 WHERE code = 'NOI'")
    _run("UPDATE app_settings SET setting_value = '10.24.0.0/16' WHERE setting_key = 'internal_networks'")
    _run("DELETE FROM app_settings WHERE setting_key = 'upload_max_mb'")
    schema = _schema()

    for _ in range(2):
        _run("DELETE FROM db_version WHERE version = 41")
        _migrate(SQUASHED)
    assert _schema() == schema
    assert _run("SELECT label, active FROM failure_modes WHERE code = 'NOI'") == [{"label": "Noisy", "active": 0}]
    assert _run("SELECT setting_value FROM app_settings WHERE setting_key = 'internal_networks'") == [
        {"setting_value": "10.24.0.0/16"}]
    assert _run("SELECT setting_value FROM app_settings WHERE setting_key = 'upload_max_mb'") == [
        {"setting_value": "20"}]
    assert _versions() == [41]
