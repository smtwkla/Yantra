"""v22, parts used (S020 § 4, § 3 Tests), in the upgrade database vel_yantra_upgrade that
test_migration_v20.py and test_migration_v21.py also use (pytest runs the files one after another,
so they do not collide).  The shared test database already has v22 when the tests start, so the
upgrade is run here: a v21 database gets ticket_parts with its columns, two CHECKs, two foreign
keys and three indexes; a re-run changes nothing.  Needs the dev MariaDB container.
"""

import pymysql
import pytest

import local_db
from tests.test_migration_v20 import _migrate, _recreate, _run, _schema

V21 = [m for m in local_db._MIGRATIONS if m[0] in (20, 21)]
V22 = [m for m in local_db._MIGRATIONS if m[0] in (20, 21, 22)]


def _versions():
    return [r["version"] for r in _run("SELECT version FROM db_version ORDER BY version")]


def _columns():
    return {r["COLUMN_NAME"]: (r["COLUMN_TYPE"], r["IS_NULLABLE"], r["COLUMN_DEFAULT"]) for r in _run(
        "SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT FROM information_schema.COLUMNS"
        " WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ticket_parts'")}


def _fill_one_ticket():
    """The shortest chain a parts line needs: a machine and one ticket on it."""
    _run("INSERT INTO sites (code, name, created_by) VALUES ('SMTW', 'SMTW plant', 'kla')")
    _run("INSERT INTO units (site_id, code, name, created_by) SELECT id, 'MCC1', 'MCC1', 'kla' FROM sites")
    _run("INSERT INTO equipment_classes (code, name, created_by) VALUES ('HP', 'Hydraulic press', 'kla')")
    _run("INSERT INTO manufacturers (name, created_by) VALUES ('Generic', 'kla')")
    _run("INSERT INTO equipment_models (manufacturer_id, designation, class_id, created_by)"
         " SELECT m.id, 'HP-1', c.id, 'kla' FROM manufacturers m, equipment_classes c")
    _run("INSERT INTO equipment (code, level, unit_id, class_id, model_id, name, created_by)"
         " SELECT 'HP001', 'equipment', u.id, m.class_id, m.id, 'Press', 'kla' FROM units u, equipment_models m")
    _run("INSERT INTO tickets (serial, equipment_id, unit_id, intensity, state, description, occurred_at, created_by)"
         " SELECT 'TK-2026-10-001', e.id, e.unit_id, 'critical', 'in_progress', 'Stopped', '2026-10-21 09:00:00',"
         " 'kla' FROM equipment e")


def _add_line(part_number, number_kind, quantity):
    _run("INSERT INTO ticket_parts (ticket_id, node_id, description, part_number, number_kind, quantity, created_by)"
         " SELECT t.id, t.equipment_id, 'Bearing', %s, %s, %s, 'kla' FROM tickets t",
         (part_number, number_kind, quantity))


def test_a_v21_database_gets_v22():
    _recreate()
    _migrate(V21)
    assert _versions() == [20, 21]
    tickets_before = _run("SELECT * FROM tickets")

    _migrate(V22)
    assert _versions() == [20, 21, 22]
    assert _run("SELECT * FROM tickets") == tickets_before

    assert _columns() == {
        "id": ("int(11)", "NO", None),
        "ticket_id": ("int(11)", "NO", None),
        "node_id": ("int(11)", "NO", None),
        "description": ("varchar(200)", "NO", None),
        "part_number": ("varchar(60)", "YES", "NULL"),
        "number_kind": ("enum('maker','generic')", "YES", "NULL"),
        "maker": ("varchar(100)", "YES", "NULL"),
        "quantity": ("decimal(6,2)", "NO", None),
        "qty_unit": ("varchar(8)", "NO", "'nos'"),
        "created_at": ("datetime", "NO", "current_timestamp()"),
        "created_by": ("varchar(100)", "NO", None),
        "updated_at": ("datetime", "YES", "NULL"),
        "updated_by": ("varchar(100)", "YES", "NULL"),
    }
    checks = {r["CONSTRAINT_NAME"] for r in _run(
        "SELECT CONSTRAINT_NAME FROM information_schema.CHECK_CONSTRAINTS"
        " WHERE CONSTRAINT_SCHEMA = DATABASE() AND TABLE_NAME = 'ticket_parts'")}
    assert checks == {"chk_ticket_parts_kind", "chk_ticket_parts_quantity"}
    foreign_keys = {(r["CONSTRAINT_NAME"], r["COLUMN_NAME"], r["REFERENCED_TABLE_NAME"]) for r in _run(
        "SELECT CONSTRAINT_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME FROM information_schema.KEY_COLUMN_USAGE"
        " WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ticket_parts' AND REFERENCED_TABLE_NAME IS NOT NULL")}
    assert foreign_keys == {("fk_ticket_parts_ticket", "ticket_id", "tickets"),
                            ("fk_ticket_parts_node", "node_id", "equipment")}
    indexes = {(r["INDEX_NAME"], r["COLUMN_NAME"]) for r in _run(
        "SELECT INDEX_NAME, COLUMN_NAME FROM information_schema.STATISTICS"
        " WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ticket_parts' AND INDEX_NAME LIKE 'ix_%%'")}
    assert indexes == {("ix_ticket_parts_ticket", "ticket_id"), ("ix_ticket_parts_node", "node_id"),
                       ("ix_ticket_parts_number", "part_number")}

    # Re-run: v22 twice is a no-op
    schema = _schema()
    _run("DELETE FROM db_version WHERE version = 22")
    _migrate(V22)
    assert _versions() == [20, 21, 22]
    assert _schema() == schema


def test_the_checks_hold_in_the_database():
    """A number and its kind come together; a quantity is above 0 (the core refuses first; the
    database keeps the rule for any other writer)."""
    _recreate()
    _migrate(V22)
    _fill_one_ticket()
    _add_line("6205-2RS", "generic", "1.50")
    _add_line(None, None, "2")
    for part_number, number_kind, quantity in (("6205-2RS", None, "1"), (None, "maker", "1"),
                                               ("6205-2RS", "generic", "0")):
        with pytest.raises(pymysql.err.OperationalError) as refused:
            _add_line(part_number, number_kind, quantity)
        assert refused.value.args[0] == 4025      # ER_CONSTRAINT_FAILED
    assert [str(r["quantity"]) for r in _run("SELECT quantity FROM ticket_parts ORDER BY id")] == ["1.50", "2.00"]
