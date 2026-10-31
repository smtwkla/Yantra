"""v44, the machines a contract covers (S081 § 4.1, § 8.1), in the upgrade database UPGRADE_DB that the v20-v43
migration tests also use (one per test run and worker, tests/db_names.py).  A fresh database gets the table
contract_equipment with its keys, foreign keys and price CHECK, and the history's two new kinds at the end of the
ENUM; a v43 database with a contract, a machine and a history line of every older kind keeps every row; the CHECK
refuses a negative price and passes the bounds; a node twice on one contract and an unknown contract or node are
refused; a re-run changes nothing.  Needs the dev MariaDB container.
"""

import pymysql
import pytest

import local_db
from tests.migration_helpers import _migrate, _recreate, _run, _schema
from tests.test_migration_v22 import _fill_one_ticket
from tests.test_migration_v36 import _foreign_keys, _keys

V43 = [m for m in local_db._MIGRATIONS if m[0] in range(20, 44)]
V44 = [m for m in local_db._MIGRATIONS if m[0] in range(20, 45)]
VERSIONS = [41, *range(42, 45)]

OLD_KINDS = ("created", "moved_unit", "moved_parent", "lifecycle", "criticality", "class", "type", "model",
             "meter_added", "meter_removed", "meter_limits", "property")
OLD_TABLES = ("sites", "units", "equipment", "equipment_events", "vendors", "contracts", "tickets")
ER_CONSTRAINT_FAILED = 4025
ER_DUPLICATE_ENTRY = 1062
ER_NO_REFERENCED_ROW = 1452


def _versions():
    return [r["version"] for r in _run("SELECT version FROM db_version ORDER BY version")]


def _a_v43_database_with_a_contract_and_a_machine():
    """A site, a unit, a machine with a history line of each older kind, a vendor and a contract -> their ids."""
    _recreate()
    _migrate(V43)
    _fill_one_ticket()
    equipment_id = _run("SELECT id FROM equipment WHERE code = 'HP001'")[0]["id"]
    for kind in OLD_KINDS:
        _run("INSERT INTO equipment_events (equipment_id, event, old_value, new_value, created_by)"
             " VALUES (%s, %s, 'a', 'b', 'kla')", (equipment_id, kind))
    _run("INSERT INTO vendors (name, created_by) VALUES ('Atlas Copco', 'kla')")
    _run("INSERT INTO contracts (site_id, vendor_id, contract_type, title, from_date, to_date, created_by)"
         " SELECT s.id, v.id, 'amc', 'Atlas Copco AMC 2026-27', '2026-04-01', '2027-03-31', 'kla'"
         " FROM sites s, vendors v")
    return _run("SELECT id FROM contracts")[0]["id"], equipment_id


def _fresh_v44():
    ids = _a_v43_database_with_a_contract_and_a_machine()
    _migrate(V44)
    return ids


def _add_line(contract_id, equipment_id, price=None):
    _run("INSERT INTO contract_equipment (contract_id, equipment_id, price, created_by) VALUES (%s, %s, %s, 'kla')",
         (contract_id, equipment_id, price))


def _second_machine():
    _run("INSERT INTO equipment (code, level, unit_id, class_id, model_id, name, created_by)"
         " SELECT 'HP002', 'equipment', unit_id, class_id, model_id, 'Press 2', 'kla' FROM equipment"
         " WHERE code = 'HP001'")
    return _run("SELECT id FROM equipment WHERE code = 'HP002'")[0]["id"]


def test_a_fresh_database_gets_v44():
    _recreate()
    _migrate(V44)
    assert _versions() == VERSIONS
    assert _run("SELECT COUNT(*) AS n FROM contract_equipment") == [{"n": 0}]
    assert _keys("contract_equipment") == [
        {"INDEX_NAME": "ix_contract_equipment_equipment", "NON_UNIQUE": 1, "cols": "equipment_id"},
        {"INDEX_NAME": "PRIMARY", "NON_UNIQUE": 0, "cols": "id"},
        {"INDEX_NAME": "uq_contract_equipment", "NON_UNIQUE": 0, "cols": "contract_id,equipment_id"},
    ]
    assert _foreign_keys("contract_equipment") == [
        {"CONSTRAINT_NAME": "fk_contract_equipment_contract", "REFERENCED_TABLE_NAME": "contracts"},
        {"CONSTRAINT_NAME": "fk_contract_equipment_equipment", "REFERENCED_TABLE_NAME": "equipment"},
    ]
    checks = [r["CONSTRAINT_NAME"] for r in _run(
        "SELECT CONSTRAINT_NAME FROM information_schema.CHECK_CONSTRAINTS WHERE CONSTRAINT_SCHEMA = DATABASE()"
        " AND TABLE_NAME = 'contract_equipment'")]
    assert checks == ["chk_contract_equipment_price"]
    price = _run("SELECT COLUMN_TYPE, IS_NULLABLE FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE()"
                 " AND TABLE_NAME = 'contract_equipment' AND COLUMN_NAME = 'price'")
    assert price == [{"COLUMN_TYPE": "decimal(10,2)", "IS_NULLABLE": "YES"}]
    event = _run("SELECT COLUMN_TYPE FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE()"
                 " AND TABLE_NAME = 'equipment_events' AND COLUMN_NAME = 'event'")[0]["COLUMN_TYPE"]
    assert event.endswith(",'property','contract_added','contract_removed')")


def test_a_v43_database_keeps_every_row():
    _a_v43_database_with_a_contract_and_a_machine()
    kept = {table: _run(f"SELECT * FROM {table} ORDER BY id") for table in OLD_TABLES}
    _migrate(V44)
    assert _versions() == VERSIONS
    assert {table: _run(f"SELECT * FROM {table} ORDER BY id") for table in OLD_TABLES} == kept
    assert sorted(r["event"] for r in _run("SELECT event FROM equipment_events")) == sorted(OLD_KINDS)


def test_the_price_check():
    contract_id, equipment_id = _fresh_v44()
    with pytest.raises(pymysql.err.OperationalError) as refused:
        _add_line(contract_id, equipment_id, "-0.01")
    assert refused.value.args[0] == ER_CONSTRAINT_FAILED and "chk_contract_equipment_price" in refused.value.args[1]
    _add_line(contract_id, equipment_id, "0")
    _add_line(contract_id, _second_machine(), "99999999.99")
    assert [str(r["price"]) for r in _run("SELECT price FROM contract_equipment ORDER BY id")] == [
        "0.00", "99999999.99"]


def test_a_node_twice_and_unknown_rows_are_refused():
    contract_id, equipment_id = _fresh_v44()
    _add_line(contract_id, equipment_id)
    with pytest.raises(pymysql.err.IntegrityError) as refused:
        _add_line(contract_id, equipment_id, "10")
    assert refused.value.args[0] == ER_DUPLICATE_ENTRY and "uq_contract_equipment" in refused.value.args[1]
    for bad_contract, bad_node, key in ((999999, equipment_id, "fk_contract_equipment_contract"),
                                        (contract_id, 999999, "fk_contract_equipment_equipment")):
        with pytest.raises(pymysql.err.IntegrityError) as refused:
            _add_line(bad_contract, bad_node)
        assert refused.value.args[0] == ER_NO_REFERENCED_ROW and key in refused.value.args[1]


def test_the_new_history_kinds_are_stored():
    _contract_id, equipment_id = _fresh_v44()
    for kind in ("contract_added", "contract_removed"):
        _run("INSERT INTO equipment_events (equipment_id, event, old_value, new_value, created_by)"
             " VALUES (%s, %s, NULL, 'x', 'kla')", (equipment_id, kind))
    assert _run("SELECT COUNT(*) AS n FROM equipment_events WHERE event IN ('contract_added', 'contract_removed')") == [{"n": 2}]


def test_a_rerun_changes_nothing():
    contract_id, equipment_id = _fresh_v44()
    _add_line(contract_id, equipment_id, "9809")
    schema = _schema()
    kept = _run("SELECT * FROM contract_equipment")
    _run("DELETE FROM db_version WHERE version = 44")
    _migrate(V44)
    assert _schema() == schema
    assert _run("SELECT * FROM contract_equipment") == kept
    assert _versions() == VERSIONS
