"""v35, equipment categories (S063 § 4.1, § 8.1), in the upgrade database UPGRADE_DB that the v20-v34
migration tests also use (one per test run and worker, tests/db_names.py).  A fresh database gets
the empty table, the class's nullable column and its foreign key; a v34 database keeps every row,
each class with no category; a re-run changes nothing.  Needs the dev MariaDB container.
"""

import pymysql
import pytest

import local_db
from tests.test_migration_v20 import _migrate, _recreate, _run, _schema
from tests.test_migration_v22 import _fill_one_ticket

V34 = [m for m in local_db._MIGRATIONS if m[0] in range(20, 35)]
V35 = [m for m in local_db._MIGRATIONS if m[0] in range(20, 36)]
VERSIONS = list(range(20, 36))

OLD_TABLES = ("sites", "units", "equipment_classes", "equipment_types", "manufacturers", "equipment_models",
              "equipment", "equipment_events", "tickets")
ER_NO_REFERENCED_ROW = 1452


def _versions():
    return [r["version"] for r in _run("SELECT version FROM db_version ORDER BY version")]


def _old_rows():
    return {table: _run(f"SELECT * FROM {table}") for table in OLD_TABLES}


def _category_column():
    return _run("SELECT COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT FROM information_schema.COLUMNS"
                " WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'equipment_classes'"
                " AND COLUMN_NAME = 'category_id'")


def _category_keys():
    return _run("SELECT CONSTRAINT_NAME, REFERENCED_TABLE_NAME FROM information_schema.REFERENTIAL_CONSTRAINTS"
                " WHERE CONSTRAINT_SCHEMA = DATABASE() AND TABLE_NAME = 'equipment_classes'"
                " AND REFERENCED_TABLE_NAME = 'equipment_categories'")


def test_a_fresh_database_gets_v35():
    _recreate()
    _migrate(V35)
    assert _versions() == VERSIONS
    assert _run("SELECT COUNT(*) AS n FROM equipment_categories") == [{"n": 0}]   # nothing seeded (Q1)
    assert _category_column() == [{"COLUMN_TYPE": "int(11)", "IS_NULLABLE": "YES", "COLUMN_DEFAULT": "NULL"}]
    assert _category_keys() == [{"CONSTRAINT_NAME": "fk_equipment_classes_category",
                                 "REFERENCED_TABLE_NAME": "equipment_categories"}]


def test_the_key_refuses_an_unknown_category():
    _recreate()
    _migrate(V35)
    _run("INSERT INTO equipment_classes (code, name, created_by) VALUES ('KEY', 'Key test', 'kla')")
    with pytest.raises(pymysql.err.IntegrityError) as refused:
        _run("UPDATE equipment_classes SET category_id = 999 WHERE code = 'KEY'")
    assert refused.value.args[0] == ER_NO_REFERENCED_ROW


def test_a_v34_database_keeps_every_row():
    _recreate()
    _migrate(V34)
    _fill_one_ticket()
    before = _old_rows()
    assert before["equipment_classes"]
    _migrate(V35)
    assert _versions() == VERSIONS
    after = _old_rows()
    assert [{k: v for k, v in r.items() if k != "category_id"} for r in after["equipment_classes"]] == (
        before["equipment_classes"])
    assert all(r["category_id"] is None for r in after["equipment_classes"])
    for table in set(OLD_TABLES) - {"equipment_classes"}:
        assert after[table] == before[table], table


def test_a_rerun_changes_nothing():
    _recreate()
    _migrate(V35)
    _fill_one_ticket()
    _run("INSERT INTO equipment_categories (name, created_by) VALUES ('Lifting equipment', 'kla')")
    _run("UPDATE equipment_classes SET category_id = (SELECT id FROM equipment_categories)")
    schema, rows = _schema(), _old_rows()
    categories = _run("SELECT * FROM equipment_categories")
    _run("DELETE FROM db_version WHERE version = 35")
    _migrate(V35)
    assert (_schema(), _old_rows()) == (schema, rows)
    assert _run("SELECT * FROM equipment_categories") == categories
    assert len(_category_keys()) == 1
    assert _versions() == VERSIONS
