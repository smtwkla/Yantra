"""v33, an equipment item's own property values (S044 § 4, § 8.3), in the upgrade database
UPGRADE_DB that the v20-v32 migration tests also use (one per test run and worker,
tests/db_names.py).  A fresh database gets the table with its keys and CHECK and the widened
event ENUM; a v32 database with equipment, model values and events keeps every row; a re-run
changes nothing.  Needs the dev MariaDB container.
"""

import pymysql
import pytest

import local_db
from tests.test_migration_v20 import _migrate, _recreate, _run, _schema
from tests.test_migration_v22 import _fill_one_ticket

V32 = [m for m in local_db._MIGRATIONS if m[0] in range(20, 33)]
V33 = [m for m in local_db._MIGRATIONS if m[0] in range(20, 34)]
VERSIONS = list(range(20, 34))

NEW_TABLE = "equipment_property_values"
OLD_TABLES = ("sites", "units", "equipment_classes", "manufacturers", "equipment_models", "equipment",
              "equipment_events", "tickets", "property_definitions", "property_options", "class_properties",
              "model_property_values", "meter_readings")
ER_NO_REFERENCED_ROW = 1452
ER_CHECK_CONSTRAINT = 4025
ER_TRUNCATED = 1265   # an ENUM value outside the list (strict mode)


def _versions():
    return [r["version"] for r in _run("SELECT version FROM db_version ORDER BY version")]


def _old_rows():
    return {table: _run(f"SELECT * FROM {table}") for table in OLD_TABLES}


def _property(name):
    return _run("SELECT id FROM property_definitions WHERE name = %s", (name,))[0]["id"]


def _insert_value(equipment_id, property_id, **columns):
    values = {"equipment_id": equipment_id, "property_id": property_id, **columns}
    _run(f"INSERT INTO {NEW_TABLE} ({', '.join(values)}) VALUES ({', '.join(['%s'] * len(values))})",
         tuple(values.values()))


def _event(equipment_id, event):
    _run("INSERT INTO equipment_events (equipment_id, event, old_value, new_value, created_by)"
         " VALUES (%s, %s, 'a', 'b', 'kla')", (equipment_id, event))


def test_a_fresh_database_gets_v33():
    _recreate()
    _migrate(V33)
    assert _versions() == VERSIONS
    columns = {r["COLUMN_NAME"]: r for r in _run(
        "SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE FROM information_schema.COLUMNS"
        " WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s", (NEW_TABLE,))}
    assert list(columns) == ["equipment_id", "property_id", "value_number", "value_text", "value_bool", "option_id",
                             "updated_at", "updated_by"]
    assert columns["value_number"]["COLUMN_TYPE"] == "decimal(16,4)"
    assert columns["value_text"]["COLUMN_TYPE"] == "varchar(100)"
    key = [r["COLUMN_NAME"] for r in _run(
        "SELECT COLUMN_NAME FROM information_schema.STATISTICS WHERE TABLE_SCHEMA = DATABASE()"
        " AND TABLE_NAME = %s AND INDEX_NAME = 'PRIMARY' ORDER BY SEQ_IN_INDEX", (NEW_TABLE,))]
    assert key == ["equipment_id", "property_id"]
    fks = {r["CONSTRAINT_NAME"]: r["REFERENCED_TABLE_NAME"] for r in _run(
        "SELECT CONSTRAINT_NAME, REFERENCED_TABLE_NAME FROM information_schema.REFERENTIAL_CONSTRAINTS"
        " WHERE CONSTRAINT_SCHEMA = DATABASE() AND TABLE_NAME = %s", (NEW_TABLE,))}
    assert fks == {"fk_equipment_property_values_node": "equipment",
                   "fk_equipment_property_values_property": "property_definitions",
                   "fk_equipment_property_values_option": "property_options"}
    event = _run("SELECT COLUMN_TYPE FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE()"
                 " AND TABLE_NAME = 'equipment_events' AND COLUMN_NAME = 'event'")[0]["COLUMN_TYPE"]
    assert event.endswith(",'meter_limits','property')")


def test_the_database_keeps_one_value_and_the_option_s_property():
    _recreate()
    _migrate(V33)
    _fill_one_ticket()
    node = _run("SELECT id FROM equipment")[0]["id"]
    frame, orientation, sealing = _property("Frame size"), _property("Shaft orientation"), _property("Shaft sealing")
    _insert_value(node, frame, value_text="132M")
    assert _run(f"SELECT value_text FROM {NEW_TABLE}")[0]["value_text"] == "132M"
    # Exactly one value column filled
    for columns in ({}, {"value_text": "x", "value_number": 1}):
        with pytest.raises(pymysql.err.OperationalError) as refused:
            _insert_value(node, _property("Speed"), **columns)
        assert refused.value.args[0] == ER_CHECK_CONSTRAINT
    # The option must be this property's (the composite FK)
    sealing_option = _run("SELECT id FROM property_options WHERE property_id = %s LIMIT 1", (sealing,))[0]["id"]
    with pytest.raises(pymysql.err.IntegrityError) as refused:
        _insert_value(node, orientation, option_id=sealing_option)
    assert refused.value.args[0] == ER_NO_REFERENCED_ROW
    with pytest.raises(pymysql.err.IntegrityError) as refused:
        _insert_value(999999, frame, value_text="x")
    assert refused.value.args[0] == ER_NO_REFERENCED_ROW
    _event(node, "property")
    with pytest.raises(pymysql.err.DataError) as refused:
        _event(node, "nameplate")
    assert refused.value.args[0] == ER_TRUNCATED


def test_a_v32_database_with_equipment_keeps_every_row():
    _recreate()
    _migrate(V32)
    _fill_one_ticket()
    node = _run("SELECT id FROM equipment")[0]["id"]
    _run("INSERT INTO model_property_values (model_id, property_id, value_number)"
         " SELECT m.id, p.id, 7.5 FROM equipment_models m, property_definitions p WHERE p.name = 'Speed'")
    _event(node, "meter_limits")
    before, schema_before = _old_rows(), _schema()
    _migrate(V33)
    assert _versions() == VERSIONS
    assert _old_rows() == before
    # Only the event ENUM of the old tables changed: every other column is as it was
    def is_event(column):   # (TABLE_NAME, ORDINAL_POSITION, COLUMN_NAME, ...)
        return column[0] == "equipment_events" and column[2] == "event"

    unchanged = [c for c in _schema()["columns"] if c[0] != NEW_TABLE and not is_event(c)]
    assert unchanged == [c for c in schema_before["columns"] if not is_event(c)]
    assert _run(f"SELECT COUNT(*) AS n FROM {NEW_TABLE}")[0]["n"] == 0


def test_a_rerun_changes_nothing():
    _recreate()
    _migrate(V33)
    _fill_one_ticket()
    node = _run("SELECT id FROM equipment")[0]["id"]
    _insert_value(node, _property("Frame size"), value_text="132M")
    _event(node, "property")
    schema, rows = _schema(), (_run(f"SELECT * FROM {NEW_TABLE}"), _run("SELECT * FROM equipment_events"))
    _run("DELETE FROM db_version WHERE version = 33")
    _migrate(V33)
    assert (_schema(), (_run(f"SELECT * FROM {NEW_TABLE}"), _run("SELECT * FROM equipment_events"))) == (schema, rows)
    assert _versions() == VERSIONS
