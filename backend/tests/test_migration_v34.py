"""v34, properties for every class, per-machine values and the Location type (S061 § 4, § 8.3), in
the upgrade database UPGRADE_DB that the v20-v33 migration tests also use (one per test run and
worker, tests/db_names.py).  A fresh database gets the flags, the ENUM value, the value columns,
the six CHECKs and the seed row; an empty database passes the precondition; a v33 database with
model values, item values and events keeps every row; a re-run changes nothing; the
precondition refuses a hand-made "GPS location".  Needs the dev MariaDB container.
"""

from decimal import Decimal

import pymysql
import pytest

import local_db
from local_db import MigrationBlocked
from tests.test_migration_v20 import _migrate, _recreate, _run, _schema
from tests.test_migration_v22 import _fill_one_ticket

V33 = [m for m in local_db._MIGRATIONS if m[0] in range(20, 34)]
V34 = [m for m in local_db._MIGRATIONS if m[0] in range(20, 35)]
VERSIONS = list(range(20, 35))

VALUE_TABLES = ("model_property_values", "equipment_property_values")
OLD_TABLES = ("sites", "units", "equipment_classes", "manufacturers", "equipment_models", "equipment",
              "equipment_events", "property_definitions", "property_options", "class_properties",
              *VALUE_TABLES)
ER_CHECK_CONSTRAINT = 4025
REFUSAL = ("A property named GPS location already exists. Rename it in Masters › Properties; "
           "the update then adds the new one.")


def _versions():
    return [r["version"] for r in _run("SELECT version FROM db_version ORDER BY version")]


def _columns(table):
    return {r["COLUMN_NAME"]: r for r in _run(
        "SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT FROM information_schema.COLUMNS"
        " WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s ORDER BY ORDINAL_POSITION", (table,))}


def _checks(table):
    return {r["CONSTRAINT_NAME"] for r in _run(
        "SELECT CONSTRAINT_NAME FROM information_schema.CHECK_CONSTRAINTS"
        " WHERE CONSTRAINT_SCHEMA = DATABASE() AND TABLE_NAME = %s", (table,))}


def _property(name):
    return _run("SELECT id FROM property_definitions WHERE name = %s", (name,))[0]["id"]


def _old_rows():
    return {table: _run(f"SELECT * FROM {table}") for table in OLD_TABLES}


def _insert(table, owner_column, owner_id, property_id, **columns):
    values = {owner_column: owner_id, "property_id": property_id, **columns}
    _run(f"INSERT INTO {table} ({', '.join(values)}) VALUES ({', '.join(['%s'] * len(values))})",
         tuple(values.values()))


def test_a_fresh_database_gets_v34():
    _recreate()
    _migrate(V34)   # the precondition passes while property_definitions does not exist yet (BR1-01)
    assert _versions() == VERSIONS
    columns = _columns("property_definitions")
    assert columns["data_type"]["COLUMN_TYPE"] == "enum('number','choice','text','yes_no','geo')"
    for flag in ("all_classes", "per_item_only"):
        assert (columns[flag]["COLUMN_TYPE"], columns[flag]["IS_NULLABLE"], columns[flag]["COLUMN_DEFAULT"]) == (
            "tinyint(1)", "NO", "0")
    for table in VALUE_TABLES:
        columns = _columns(table)
        assert (columns["value_lat"]["COLUMN_TYPE"], columns["value_lat"]["IS_NULLABLE"]) == ("decimal(8,6)", "YES")
        assert (columns["value_lng"]["COLUMN_TYPE"], columns["value_lng"]["IS_NULLABLE"]) == ("decimal(9,6)", "YES")
        short = table.split("_")[0]
        assert {f"chk_{short}_property_one_value", f"chk_{short}_property_geo_pair",
                f"chk_{short}_property_geo_range"} <= _checks(table)
    seed = _run("SELECT data_type, unit, all_classes, per_item_only, active, created_by FROM property_definitions"
                " WHERE name = 'GPS location'")
    assert seed == [{"data_type": "geo", "unit": None, "all_classes": 1, "per_item_only": 1, "active": 1,
                     "created_by": "migration-v34"}]


def test_the_checks_refuse_a_broken_location():
    _recreate()
    _migrate(V34)
    _fill_one_ticket()
    node = _run("SELECT id FROM equipment")[0]["id"]
    model = _run("SELECT id FROM equipment_models")[0]["id"]
    gps = _property("GPS location")
    _insert("equipment_property_values", "equipment_id", node, gps, value_lat="11.016823", value_lng="76.955812")
    assert _run("SELECT value_lat, value_lng FROM equipment_property_values")[0] == {
        "value_lat": Decimal("11.016823"), "value_lng": Decimal("76.955812")}
    _insert("model_property_values", "model_id", model, gps, value_lat="-90", value_lng="180")
    refused_rows = (
        {"value_lat": "11"},                                     # a latitude without a longitude
        {"value_lng": "76"},                                     # a longitude without a latitude
        {"value_lat": "11", "value_lng": "76", "value_text": "x"},   # two value slots
        {"value_lat": "91", "value_lng": "76"},                  # out of range
        {"value_lat": "11", "value_lng": "-180.5"},
    )
    for columns in refused_rows:
        for table, owner_column, owner_id in (("equipment_property_values", "equipment_id", node),
                                              ("model_property_values", "model_id", model)):
            with pytest.raises(pymysql.err.OperationalError) as refused:
                _insert(table, owner_column, owner_id, _property("Speed"), **columns)
            assert refused.value.args[0] == ER_CHECK_CONSTRAINT, (table, columns)


def test_a_v33_database_with_values_keeps_every_row():
    _recreate()
    _migrate(V33)
    _fill_one_ticket()
    node = _run("SELECT id FROM equipment")[0]["id"]
    model = _run("SELECT id FROM equipment_models")[0]["id"]
    _insert("model_property_values", "model_id", model, _property("Speed"), value_number=1440)
    _insert("equipment_property_values", "equipment_id", node, _property("Frame size"), value_text="132M")
    _run("INSERT INTO equipment_events (equipment_id, event, old_value, new_value, created_by)"
         " VALUES (%s, 'property', 'Frame size: no value (model)', 'Frame size: 132M', 'kla')", (node,))
    before = _old_rows()
    _migrate(V34)
    assert _versions() == VERSIONS
    after = _old_rows()
    # The old rows are unchanged; the new columns are NULL or 0 on each, and the seed is the one new row
    for table in VALUE_TABLES:
        assert [{k: v for k, v in r.items() if k not in ("value_lat", "value_lng")} for r in after[table]] == (
            before[table])
        assert all(r["value_lat"] is None and r["value_lng"] is None for r in after[table])
    old_properties = [{k: v for k, v in r.items() if k not in ("all_classes", "per_item_only")}
                      for r in after["property_definitions"] if r["created_by"] != "migration-v34"]
    assert old_properties == before["property_definitions"]
    assert all(r["all_classes"] == 0 and r["per_item_only"] == 0 for r in after["property_definitions"]
               if r["created_by"] != "migration-v34")
    for table in set(OLD_TABLES) - {*VALUE_TABLES, "property_definitions"}:
        assert after[table] == before[table], table


def test_a_rerun_changes_nothing():
    _recreate()
    _migrate(V34)
    _fill_one_ticket()
    node = _run("SELECT id FROM equipment")[0]["id"]
    _insert("equipment_property_values", "equipment_id", node, _property("GPS location"),
            value_lat="11.016823", value_lng="76.955812")
    schema, rows = _schema(), _old_rows()
    _run("DELETE FROM db_version WHERE version = 34")
    _migrate(V34)   # the seed v34 made itself passes the precondition
    assert (_schema(), _old_rows()) == (schema, rows)
    assert _versions() == VERSIONS


def test_the_precondition_refuses_a_hand_made_gps_location():
    _recreate()
    _migrate(V33)
    _run("INSERT INTO property_definitions (name, data_type, created_by) VALUES ('gps LOCATION', 'text', 'kla')")
    schema, rows = _schema(), _old_rows()
    with pytest.raises(MigrationBlocked) as refused:
        _migrate(V34)
    assert str(refused.value) == REFUSAL
    assert 34 not in _versions()
    assert (_schema(), _old_rows()) == (schema, rows)
    # Renamed, the update goes ahead and adds the new one beside it
    _run("UPDATE property_definitions SET name = 'Old GPS' WHERE name = 'gps LOCATION'")
    _migrate(V34)
    assert _versions() == VERSIONS
    assert _run("SELECT data_type FROM property_definitions WHERE name = 'GPS location'") == [{"data_type": "geo"}]
