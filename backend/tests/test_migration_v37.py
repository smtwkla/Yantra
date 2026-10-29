"""v37, the why-why chain and the root cause (S069 § 4.1, § 8.1), in the upgrade database UPGRADE_DB that
the v20-v36 migration tests also use (one per test run and worker, tests/db_names.py).  A fresh database
gets the table improvement_whys and the three columns of improvements with their keys and CHECKs; a v36
database keeps every row and gets NULL columns; the CHECKs refuse a root cause half set and a position 0;
a re-run changes nothing (and proves ADD KEY IF NOT EXISTS).  Needs the dev MariaDB container.
"""

import pymysql
import pytest

import local_db
from tests.test_migration_v20 import _migrate, _recreate, _run, _schema
from tests.test_migration_v22 import _fill_one_ticket
from tests.test_migration_v36 import _foreign_keys, _keys, _link, _one_improvement

V36 = [m for m in local_db._MIGRATIONS if m[0] in range(20, 37)]
V37 = [m for m in local_db._MIGRATIONS if m[0] in range(20, 38)]
VERSIONS = list(range(20, 38))

OLD_TABLES = ("sites", "units", "equipment", "tickets", "people", "improvements", "improvement_tickets")
ER_CONSTRAINT_FAILED = 4025


def _versions():
    return [r["version"] for r in _run("SELECT version FROM db_version ORDER BY version")]


def _old_rows():
    return {table: _run(f"SELECT * FROM {table}") for table in OLD_TABLES}


def _checks(table):
    return _run("SELECT CONSTRAINT_NAME FROM information_schema.CHECK_CONSTRAINTS"
                " WHERE CONSTRAINT_SCHEMA = DATABASE() AND TABLE_NAME = %s ORDER BY CONSTRAINT_NAME", (table,))


def _cause_id(code):
    return _run("SELECT id FROM failure_causes WHERE code = %s", (code,))[0]["id"]


def _add_why(improvement_id, position):
    _run("INSERT INTO improvement_whys (improvement_id, position, question, answer, created_by)"
         " VALUES (%s, %s, 'Why?', 'Because', 'kla')", (improvement_id, position))


def _set_root_cause(improvement_id, text, cause_id):
    _run("UPDATE improvements SET root_cause = %s, root_cause_id = %s WHERE id = %s", (text, cause_id, improvement_id))


def test_a_fresh_database_gets_v37():
    _recreate()
    _migrate(V37)
    assert _versions() == VERSIONS
    assert _run("SELECT COUNT(*) AS n FROM improvement_whys") == [{"n": 0}]
    assert _keys("improvement_whys") == [
        {"INDEX_NAME": "ix_improvement_whys_position", "NON_UNIQUE": 1, "cols": "improvement_id,position"},
        {"INDEX_NAME": "PRIMARY", "NON_UNIQUE": 0, "cols": "id"},
    ]
    assert _foreign_keys("improvement_whys") == [
        {"CONSTRAINT_NAME": "fk_improvement_whys_improvement", "REFERENCED_TABLE_NAME": "improvements"}]
    assert _checks("improvement_whys") == [{"CONSTRAINT_NAME": "chk_improvement_whys_position"}]
    assert _run("SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE FROM information_schema.COLUMNS"
                " WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'improvements'"
                " AND COLUMN_NAME IN ('problem', 'root_cause', 'root_cause_id', 'contributing_causes')"
                " ORDER BY ORDINAL_POSITION") == [
        {"COLUMN_NAME": "problem", "COLUMN_TYPE": "varchar(2000)", "IS_NULLABLE": "NO"},
        {"COLUMN_NAME": "root_cause", "COLUMN_TYPE": "varchar(500)", "IS_NULLABLE": "YES"},
        {"COLUMN_NAME": "root_cause_id", "COLUMN_TYPE": "int(11)", "IS_NULLABLE": "YES"},
        {"COLUMN_NAME": "contributing_causes", "COLUMN_TYPE": "varchar(2000)", "IS_NULLABLE": "YES"},
    ]
    assert {"INDEX_NAME": "ix_improvements_root_cause", "NON_UNIQUE": 1, "cols": "root_cause_id"} in _keys("improvements")
    assert {"CONSTRAINT_NAME": "fk_improvements_root_cause", "REFERENCED_TABLE_NAME": "failure_causes"} in (
        _foreign_keys("improvements"))
    assert _checks("improvements") == [{"CONSTRAINT_NAME": "chk_improvements_root_cause"}]


def test_a_v36_database_keeps_every_row():
    _recreate()
    _migrate(V36)
    _fill_one_ticket()
    improvement_id = _one_improvement()
    _link(improvement_id, _run("SELECT id FROM tickets")[0]["id"], 1)
    before = _old_rows()
    _migrate(V37)
    assert _versions() == VERSIONS
    after = _old_rows()
    new_columns = ("root_cause", "root_cause_id", "contributing_causes")
    assert [{k: v for k, v in row.items() if k not in new_columns} for row in after["improvements"]] == (
        before["improvements"])
    assert [{k: row[k] for k in new_columns} for row in after["improvements"]] == [dict.fromkeys(new_columns)]
    assert {table: rows for table, rows in after.items() if table != "improvements"} == (
        {table: rows for table, rows in before.items() if table != "improvements"})


def test_the_checks_keep_the_root_cause_whole_and_positions_from_one():
    _recreate()
    _migrate(V37)
    _fill_one_ticket()
    improvement_id = _one_improvement()
    cause_id = _cause_id("4.2")
    for text, cause in (("No PM plan", None), (None, cause_id)):
        with pytest.raises(pymysql.err.OperationalError) as refused:
            _set_root_cause(improvement_id, text, cause)
        assert refused.value.args[0] == ER_CONSTRAINT_FAILED
    _set_root_cause(improvement_id, "No PM plan", cause_id)
    _set_root_cause(improvement_id, None, None)
    with pytest.raises(pymysql.err.OperationalError) as refused:
        _add_why(improvement_id, 0)
    assert refused.value.args[0] == ER_CONSTRAINT_FAILED
    _add_why(improvement_id, 1)
    assert _run("SELECT position FROM improvement_whys") == [{"position": 1}]


def test_a_rerun_changes_nothing():
    _recreate()
    _migrate(V37)
    _fill_one_ticket()
    improvement_id = _one_improvement()
    _add_why(improvement_id, 1)
    _set_root_cause(improvement_id, "No PM plan", _cause_id("4.2"))
    schema = _schema()
    kept = (_run("SELECT * FROM improvements"), _run("SELECT * FROM improvement_whys"))
    _run("DELETE FROM db_version WHERE version = 37")
    _migrate(V37)
    assert _schema() == schema
    assert (_run("SELECT * FROM improvements"), _run("SELECT * FROM improvement_whys")) == kept
    assert _versions() == VERSIONS
