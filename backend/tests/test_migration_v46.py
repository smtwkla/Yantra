"""v46, the contract reminders' markers (S084 § 4.1, § 8.1), in the upgrade database UPGRADE_DB that the v20-v45
migration tests also use (one per test run and worker, tests/db_names.py).  A fresh database gets
contracts.first_reminder_for and second_reminder_for, nullable dates after to_date; a v45 database with a contract
keeps it, both markers NULL; a re-run changes nothing.  Needs the dev MariaDB container.
"""

import local_db
from tests.migration_helpers import _migrate, _recreate, _run, _schema
from tests.test_migration_v43 import _a_v42_database_with_a_site_and_a_vendor, _add_contract

V45 = [m for m in local_db._MIGRATIONS if m[0] in range(20, 46)]
V46 = [m for m in local_db._MIGRATIONS if m[0] in range(20, 47)]
VERSIONS = [41, *range(42, 47)]


def _versions():
    return [r["version"] for r in _run("SELECT version FROM db_version ORDER BY version")]


def _columns():
    return _run("SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE FROM information_schema.COLUMNS"
                " WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'contracts'"
                " AND COLUMN_NAME IN ('to_date', 'first_reminder_for', 'second_reminder_for', 'covers_labour')"
                " ORDER BY ORDINAL_POSITION")


def _a_v45_database_with_a_contract():
    site_id, vendor_id = _a_v42_database_with_a_site_and_a_vendor()
    _migrate(V45)
    _add_contract(site_id, vendor_id)


def test_a_fresh_database_gets_v46():
    _recreate()
    _migrate(V46)
    assert _versions() == VERSIONS
    assert _columns() == [
        {"COLUMN_NAME": "to_date", "COLUMN_TYPE": "date", "IS_NULLABLE": "NO"},
        {"COLUMN_NAME": "first_reminder_for", "COLUMN_TYPE": "date", "IS_NULLABLE": "YES"},
        {"COLUMN_NAME": "second_reminder_for", "COLUMN_TYPE": "date", "IS_NULLABLE": "YES"},
        {"COLUMN_NAME": "covers_labour", "COLUMN_TYPE": "tinyint(1)", "IS_NULLABLE": "NO"},
    ]


def test_a_v45_database_keeps_its_contract():
    _a_v45_database_with_a_contract()
    kept = _run("SELECT id, title, to_date FROM contracts")
    _migrate(V46)
    assert _run("SELECT id, title, to_date FROM contracts") == kept
    assert _run("SELECT first_reminder_for, second_reminder_for FROM contracts") == [
        {"first_reminder_for": None, "second_reminder_for": None}]
    assert _versions() == VERSIONS


def test_a_rerun_changes_nothing():
    _a_v45_database_with_a_contract()
    _migrate(V46)
    _run("UPDATE contracts SET first_reminder_for = to_date")
    schema = _schema()
    kept = _run("SELECT * FROM contracts ORDER BY id")
    _run("DELETE FROM db_version WHERE version = 46")
    _migrate(V46)
    assert _schema() == schema
    assert _run("SELECT * FROM contracts ORDER BY id") == kept
    assert _versions() == VERSIONS
