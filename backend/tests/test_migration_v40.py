"""v40, the improvement alerts' markers (S074 § 4.1, § 8.3), in the upgrade database UPGRADE_DB that the
v20-v39 migration tests also use (one per test run and worker, tests/db_names.py).  A fresh database gets
improvement_actions.overdue_alert_for (DATE NULL, after due_date) and improvements.ready_alert_for (DATETIME
NULL, after watch_from); a v39 database with rows keeps every row, the new columns NULL; a re-run changes
nothing.  Needs the dev MariaDB container.
"""

import local_db
from tests.test_migration_v20 import _migrate, _recreate, _run, _schema
from tests.test_migration_v22 import _fill_one_ticket
from tests.test_migration_v36 import _one_improvement
from tests.test_migration_v38 import _add_action

V39 = [m for m in local_db._MIGRATIONS if m[0] in range(20, 40)]
V40 = [m for m in local_db._MIGRATIONS if m[0] in range(20, 41)]
VERSIONS = list(range(20, 41))


def _versions():
    return [r["version"] for r in _run("SELECT version FROM db_version ORDER BY version")]


def _column(table, column):
    rows = _run("SELECT COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT FROM information_schema.COLUMNS"
                " WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s", (table, column))
    return rows[0] if rows else None


def _column_after(table, column):
    """The column just before ``column`` in the table's order."""
    return _run("SELECT b.COLUMN_NAME FROM information_schema.COLUMNS a JOIN information_schema.COLUMNS b"
                " ON b.TABLE_SCHEMA = a.TABLE_SCHEMA AND b.TABLE_NAME = a.TABLE_NAME"
                " AND b.ORDINAL_POSITION = a.ORDINAL_POSITION - 1"
                " WHERE a.TABLE_SCHEMA = DATABASE() AND a.TABLE_NAME = %s AND a.COLUMN_NAME = %s",
                (table, column))[0]["COLUMN_NAME"]


def _a_v39_database_with_rows():
    """v39 with a ticket, an improvement and an open countermeasure -> the improvement's id."""
    _recreate()
    _migrate(V39)
    _fill_one_ticket()
    improvement_id = _one_improvement()
    _add_action(improvement_id)
    return improvement_id


def test_a_fresh_database_gets_v40():
    _recreate()
    _migrate(V40)
    assert _versions() == VERSIONS
    assert _column("improvement_actions", "overdue_alert_for") == {
        "COLUMN_TYPE": "date", "IS_NULLABLE": "YES", "COLUMN_DEFAULT": "NULL"}
    assert _column("improvements", "ready_alert_for") == {
        "COLUMN_TYPE": "datetime", "IS_NULLABLE": "YES", "COLUMN_DEFAULT": "NULL"}
    assert _column_after("improvement_actions", "overdue_alert_for") == "due_date"
    assert _column_after("improvements", "ready_alert_for") == "watch_from"


def test_a_v39_database_keeps_every_row():
    _a_v39_database_with_rows()
    before = (_run("SELECT * FROM improvements ORDER BY id"), _run("SELECT * FROM improvement_actions ORDER BY id"))
    _migrate(V40)
    improvements = _run("SELECT * FROM improvements ORDER BY id")
    actions = _run("SELECT * FROM improvement_actions ORDER BY id")
    assert [{k: v for k, v in row.items() if k != "ready_alert_for"} for row in improvements] == list(before[0])
    assert [{k: v for k, v in row.items() if k != "overdue_alert_for"} for row in actions] == list(before[1])
    assert {row["ready_alert_for"] for row in improvements} == {None}
    assert {row["overdue_alert_for"] for row in actions} == {None}


def test_a_rerun_changes_nothing():
    _a_v39_database_with_rows()
    _migrate(V40)
    _run("UPDATE improvement_actions SET overdue_alert_for = due_date")
    schema = _schema()
    kept = (_run("SELECT * FROM improvements ORDER BY id"), _run("SELECT * FROM improvement_actions ORDER BY id"))
    _run("DELETE FROM db_version WHERE version = 40")
    _migrate(V40)
    assert _schema() == schema
    assert (_run("SELECT * FROM improvements ORDER BY id"), _run("SELECT * FROM improvement_actions ORDER BY id")) == kept
    assert _versions() == VERSIONS
