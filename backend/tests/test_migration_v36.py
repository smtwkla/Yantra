"""v36, improvements and their tickets (S067 § 4.1, § 8.1), in the upgrade database UPGRADE_DB that the
v20-v35 migration tests also use (one per test run and worker, tests/db_names.py).  A fresh database gets
both tables, their keys and the CHECK; a v35 database keeps every row and gets empty tables; the unique
key allows one open link per ticket and any number of closed (NULL) ones; a re-run changes nothing.
Needs the dev MariaDB container.
"""

import pymysql
import pytest

import local_db
from tests.test_migration_v20 import _migrate, _recreate, _run, _schema
from tests.test_migration_v22 import _fill_one_ticket

V35 = [m for m in local_db._MIGRATIONS if m[0] in range(20, 36)]
V36 = [m for m in local_db._MIGRATIONS if m[0] in range(20, 37)]
VERSIONS = list(range(20, 37))

OLD_TABLES = ("sites", "units", "equipment_classes", "equipment_models", "equipment", "tickets", "serial_counters")
ER_DUP_ENTRY = 1062
ER_CONSTRAINT_FAILED = 4025


def _versions():
    return [r["version"] for r in _run("SELECT version FROM db_version ORDER BY version")]


def _old_rows():
    return {table: _run(f"SELECT * FROM {table}") for table in OLD_TABLES}


def _keys(table):
    return _run("SELECT INDEX_NAME, NON_UNIQUE, GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX) AS cols"
                " FROM information_schema.STATISTICS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s"
                " GROUP BY INDEX_NAME, NON_UNIQUE ORDER BY INDEX_NAME", (table,))


def _foreign_keys(table):
    return _run("SELECT CONSTRAINT_NAME, REFERENCED_TABLE_NAME FROM information_schema.REFERENTIAL_CONSTRAINTS"
                " WHERE CONSTRAINT_SCHEMA = DATABASE() AND TABLE_NAME = %s ORDER BY CONSTRAINT_NAME", (table,))


def _one_improvement():
    """An improvement on the one ticket of _fill_one_ticket, led by a person; -> its id."""
    _run("INSERT INTO people (name, employment, created_by) VALUES ('Lead', 'direct', 'kla')")
    _run("INSERT INTO improvements (serial, unit_id, equipment_id, title, problem, lead_id, created_by)"
         " SELECT 'IM-2026-10-001', t.unit_id, t.equipment_id, 'Dust', 'Dust in the panel', p.id, 'kla'"
         " FROM tickets t, people p")
    return _run("SELECT id FROM improvements")[0]["id"]


def _link(improvement_id, ticket_id, open_link):
    _run("INSERT INTO improvement_tickets (improvement_id, ticket_id, open_link, created_by) VALUES (%s, %s, %s, 'kla')",
         (improvement_id, ticket_id, open_link))


def test_a_fresh_database_gets_v36():
    _recreate()
    _migrate(V36)
    assert _versions() == VERSIONS
    assert _run("SELECT COUNT(*) AS n FROM improvements") == [{"n": 0}]
    assert _run("SELECT COUNT(*) AS n FROM improvement_tickets") == [{"n": 0}]
    assert _run("SELECT COLUMN_TYPE, COLUMN_DEFAULT FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE()"
                " AND TABLE_NAME = 'improvements' AND COLUMN_NAME = 'state'") == [
        {"COLUMN_TYPE": "enum('analysing')", "COLUMN_DEFAULT": "'analysing'"}]
    assert _keys("improvements") == [
        {"INDEX_NAME": "fk_improvements_lead", "NON_UNIQUE": 1, "cols": "lead_id"},
        {"INDEX_NAME": "ix_improvements_equipment", "NON_UNIQUE": 1, "cols": "equipment_id"},
        {"INDEX_NAME": "ix_improvements_unit_state", "NON_UNIQUE": 1, "cols": "unit_id,state"},
        {"INDEX_NAME": "PRIMARY", "NON_UNIQUE": 0, "cols": "id"},
        {"INDEX_NAME": "uq_improvements_serial", "NON_UNIQUE": 0, "cols": "serial"},
    ]
    assert _keys("improvement_tickets") == [
        {"INDEX_NAME": "PRIMARY", "NON_UNIQUE": 0, "cols": "improvement_id,ticket_id"},
        {"INDEX_NAME": "uq_improvement_tickets_open", "NON_UNIQUE": 0, "cols": "ticket_id,open_link"},
    ]
    assert _foreign_keys("improvements") == [
        {"CONSTRAINT_NAME": "fk_improvements_equipment", "REFERENCED_TABLE_NAME": "equipment"},
        {"CONSTRAINT_NAME": "fk_improvements_lead", "REFERENCED_TABLE_NAME": "people"},
        {"CONSTRAINT_NAME": "fk_improvements_unit", "REFERENCED_TABLE_NAME": "units"},
    ]
    assert _foreign_keys("improvement_tickets") == [
        {"CONSTRAINT_NAME": "fk_improvement_tickets_improvement", "REFERENCED_TABLE_NAME": "improvements"},
        {"CONSTRAINT_NAME": "fk_improvement_tickets_ticket", "REFERENCED_TABLE_NAME": "tickets"},
    ]
    assert _run("SELECT CONSTRAINT_NAME FROM information_schema.CHECK_CONSTRAINTS"
                " WHERE CONSTRAINT_SCHEMA = DATABASE() AND TABLE_NAME = 'improvement_tickets'") == [
        {"CONSTRAINT_NAME": "chk_improvement_tickets_open_link"}]


def test_a_v35_database_keeps_every_row():
    _recreate()
    _migrate(V35)
    _fill_one_ticket()
    before = _old_rows()
    assert before["tickets"]
    _migrate(V36)
    assert _versions() == VERSIONS
    assert _old_rows() == before
    assert _run("SELECT COUNT(*) AS n FROM improvements") == [{"n": 0}]


def test_one_open_link_per_ticket_and_any_number_of_closed_ones():
    """D4: MariaDB's unique index treats NULLs as distinct, so a ticket may sit in many closed
    improvements (open_link NULL) and in only one open one (open_link 1)."""
    _recreate()
    _migrate(V36)
    _fill_one_ticket()
    first = _one_improvement()
    _run("INSERT INTO improvements (serial, unit_id, equipment_id, title, problem, lead_id, created_by)"
         " SELECT 'IM-2026-10-002', unit_id, equipment_id, title, problem, lead_id, 'kla' FROM improvements")
    _run("INSERT INTO improvements (serial, unit_id, equipment_id, title, problem, lead_id, created_by)"
         " SELECT 'IM-2026-10-003', unit_id, equipment_id, title, problem, lead_id, 'kla' FROM improvements"
         " WHERE serial = 'IM-2026-10-001'")
    second, third = [r["id"] for r in _run("SELECT id FROM improvements WHERE id <> %s ORDER BY id", (first,))]
    ticket_id = _run("SELECT id FROM tickets")[0]["id"]

    _link(first, ticket_id, 1)
    with pytest.raises(pymysql.err.IntegrityError) as refused:
        _link(second, ticket_id, 1)
    assert refused.value.args[0] == ER_DUP_ENTRY
    assert "uq_improvement_tickets_open" in refused.value.args[1]

    _link(second, ticket_id, None)
    _link(third, ticket_id, None)
    assert _run("SELECT COUNT(*) AS n FROM improvement_tickets WHERE ticket_id = %s", (ticket_id,)) == [{"n": 3}]


def test_the_check_refuses_another_open_link_value():
    _recreate()
    _migrate(V36)
    _fill_one_ticket()
    improvement_id = _one_improvement()
    with pytest.raises(pymysql.err.OperationalError) as refused:
        _link(improvement_id, _run("SELECT id FROM tickets")[0]["id"], 2)
    assert refused.value.args[0] == ER_CONSTRAINT_FAILED


def test_a_rerun_changes_nothing():
    _recreate()
    _migrate(V36)
    _fill_one_ticket()
    improvement_id = _one_improvement()
    _link(improvement_id, _run("SELECT id FROM tickets")[0]["id"], 1)
    schema, rows = _schema(), _old_rows()
    kept = (_run("SELECT * FROM improvements"), _run("SELECT * FROM improvement_tickets"))
    _run("DELETE FROM db_version WHERE version = 36")
    _migrate(V36)
    assert (_schema(), _old_rows()) == (schema, rows)
    assert (_run("SELECT * FROM improvements"), _run("SELECT * FROM improvement_tickets")) == kept
    assert _versions() == VERSIONS
