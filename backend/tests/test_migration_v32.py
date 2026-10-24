"""v32, meter readings (S039 § 4, § 8), in the upgrade database UPGRADE_DB that the v20-v31
migration tests also use (one per test run and worker, tests/db_names.py).  A fresh database gets
the table with its foreign keys and index; a v31 database with equipment, a meter type and a model
meter keeps every row; a re-run changes nothing (BS1-08).  Needs the dev MariaDB container.
"""

import pymysql
import pytest

import local_db
from tests.test_migration_v20 import _migrate, _recreate, _run, _schema
from tests.test_migration_v22 import _fill_one_ticket

V31 = [m for m in local_db._MIGRATIONS if m[0] in range(20, 32)]
V32 = [m for m in local_db._MIGRATIONS if m[0] in range(20, 33)]
VERSIONS = list(range(20, 33))

NEW_TABLE = "meter_readings"
OLD_TABLES = ("sites", "units", "equipment_classes", "manufacturers", "equipment_models", "equipment", "tickets",
              "meter_types", "model_meters", "node_meters", "property_definitions")
ER_NO_REFERENCED_ROW = 1452
ER_TRUNCATED = 1265   # an ENUM value outside the list (strict mode)


def _versions():
    return [r["version"] for r in _run("SELECT version FROM db_version ORDER BY version")]


def _old_rows():
    return {table: _run(f"SELECT * FROM {table}") for table in OLD_TABLES}


def _insert_reading(equipment_id, meter_type_id, **columns):
    values = {"equipment_id": equipment_id, "meter_type_id": meter_type_id, "value": "12345.6",
              "taken_at": "2026-10-23 18:00:00", "created_by": "kla", **columns}
    _run(f"INSERT INTO meter_readings ({', '.join(values)}) VALUES ({', '.join(['%s'] * len(values))})",
         tuple(values.values()))


def test_a_fresh_database_gets_v32():
    _recreate()
    _migrate(V32)
    assert _versions() == VERSIONS
    columns = {r["COLUMN_NAME"]: r for r in _run(
        "SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT FROM information_schema.COLUMNS"
        " WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s", (NEW_TABLE,))}
    assert list(columns) == ["id", "equipment_id", "meter_type_id", "value", "taken_at", "is_reset", "limit_state",
                             "source", "note", "created_at", "created_by", "removed_at", "removed_by"]
    assert columns["value"]["COLUMN_TYPE"] == "decimal(14,3)"
    assert columns["limit_state"]["COLUMN_TYPE"] == "enum('low','high','not_ok')"
    assert columns["source"]["COLUMN_TYPE"] == "enum('manual','pm','move','iiot')"
    assert columns["source"]["COLUMN_DEFAULT"].strip("'") == "manual"
    fks = {r["CONSTRAINT_NAME"]: r["REFERENCED_TABLE_NAME"] for r in _run(
        "SELECT CONSTRAINT_NAME, REFERENCED_TABLE_NAME FROM information_schema.REFERENTIAL_CONSTRAINTS"
        " WHERE CONSTRAINT_SCHEMA = DATABASE() AND TABLE_NAME = %s", (NEW_TABLE,))}
    assert fks == {"fk_meter_readings_node": "equipment", "fk_meter_readings_type": "meter_types"}
    index = [r["COLUMN_NAME"] for r in _run(
        "SELECT COLUMN_NAME FROM information_schema.STATISTICS WHERE TABLE_SCHEMA = DATABASE()"
        " AND TABLE_NAME = %s AND INDEX_NAME = 'ix_meter_readings_meter_time' ORDER BY SEQ_IN_INDEX", (NEW_TABLE,))]
    assert index == ["equipment_id", "meter_type_id", "taken_at"]


def test_the_database_keeps_the_links_and_the_lists():
    _recreate()
    _migrate(V32)
    _fill_one_ticket()
    node = _run("SELECT id FROM equipment")[0]["id"]
    hours = _run("SELECT id FROM meter_types WHERE name = 'Run hours'")[0]["id"]
    _insert_reading(node, hours)
    row = _run("SELECT value, is_reset, limit_state, source, removed_at FROM meter_readings")[0]
    assert (str(row["value"]), row["is_reset"], row["limit_state"], row["source"], row["removed_at"]) == (
        "12345.600", 0, None, "manual", None)
    # Two readings may share a minute (a removed one and its replacement): no unique key
    _insert_reading(node, hours, removed_at="2026-10-23 18:05:00", removed_by="kla")
    assert _run("SELECT COUNT(*) AS n FROM meter_readings")[0]["n"] == 2
    with pytest.raises(pymysql.err.IntegrityError) as refused:
        _insert_reading(node, 999999)
    assert refused.value.args[0] == ER_NO_REFERENCED_ROW
    with pytest.raises(pymysql.err.DataError) as refused:
        _insert_reading(node, hours, limit_state="ok")
    assert refused.value.args[0] == ER_TRUNCATED


def test_a_v31_database_with_equipment_keeps_every_row():
    _recreate()
    _migrate(V31)
    _fill_one_ticket()
    _run("INSERT INTO model_meters (model_id, meter_type_id, min_value, max_value, created_by)"
         " SELECT m.id, t.id, 10, 60, 'kla' FROM equipment_models m, meter_types t WHERE t.name = 'Oil temperature'")
    _run("INSERT INTO node_meters (equipment_id, meter_type_id, own, created_by)"
         " SELECT e.id, t.id, 1, 'kla' FROM equipment e, meter_types t WHERE t.name = 'Run hours'")
    before, schema_before = _old_rows(), _schema()
    _migrate(V32)
    assert _versions() == VERSIONS
    assert _old_rows() == before
    # No existing table changed: the old tables' columns are as they were
    assert [c for c in _schema()["columns"] if c[0] != NEW_TABLE] == schema_before["columns"]
    assert _run("SELECT COUNT(*) AS n FROM meter_readings")[0]["n"] == 0


def test_a_rerun_changes_nothing():
    _recreate()
    _migrate(V32)
    _fill_one_ticket()
    _insert_reading(_run("SELECT id FROM equipment")[0]["id"],
                    _run("SELECT id FROM meter_types WHERE name = 'Run hours'")[0]["id"])
    schema, rows = _schema(), _run("SELECT * FROM meter_readings")
    _run("DELETE FROM db_version WHERE version = 32")
    _migrate(V32)
    assert (_schema(), _run("SELECT * FROM meter_readings")) == (schema, rows)
    assert _versions() == VERSIONS
