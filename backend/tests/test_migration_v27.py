"""v27, people.email (S032 § 4), in the upgrade database UPGRADE_DB that the v20-v26 migration tests
also use (one per test run and worker, tests/db_names.py).  A fresh database gets the column; a
v26 database with people gets it, NULL for every existing row, and keeps every row; a re-run
changes nothing.  Needs the dev MariaDB container.
"""

import local_db
from tests.test_migration_v20 import _migrate, _recreate, _run, _schema

V26 = [m for m in local_db._MIGRATIONS if m[0] in (20, 21, 22, 23, 24, 25, 26)]
V27 = [m for m in local_db._MIGRATIONS if m[0] in (20, 21, 22, 23, 24, 25, 26, 27)]


def _versions():
    return [r["version"] for r in _run("SELECT version FROM db_version ORDER BY version")]


def _email_column():
    rows = _run("SELECT COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT FROM information_schema.COLUMNS"
                " WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'people' AND COLUMN_NAME = 'email'")
    return rows[0] if rows else None


def _assert_column():
    column = _email_column()
    assert column["COLUMN_TYPE"] == "varchar(254)"
    assert column["IS_NULLABLE"] == "YES"
    assert column["COLUMN_DEFAULT"] in (None, "NULL")


def test_a_fresh_database_gets_v27():
    _recreate()
    _migrate(V27)
    assert _versions() == [20, 21, 22, 23, 24, 25, 26, 27]
    _assert_column()


def test_a_v26_database_gets_v27_null_for_existing_people():
    _recreate()
    _migrate(V26)
    _run("INSERT INTO people (name, employment, username, created_by) VALUES ('Priya', 'direct', 'priya', 'kla'),"
         " ('Ravi', 'direct', NULL, 'kla')")
    before = _run("SELECT * FROM people ORDER BY id")
    assert _email_column() is None

    _migrate(V27)
    assert _versions() == [20, 21, 22, 23, 24, 25, 26, 27]
    _assert_column()
    after = _run("SELECT * FROM people ORDER BY id")
    assert [row.pop("email") for row in after] == [None, None]
    assert after == before


def test_running_v27_again_changes_nothing():
    _recreate()
    _migrate(V27)
    schema = _schema()
    _run("DELETE FROM db_version WHERE version = 27")
    _migrate(V27)
    assert _versions() == [20, 21, 22, 23, 24, 25, 26, 27]
    assert _schema() == schema
