"""v22, parts used (S020 § 4, § 3 Tests) — now part of the squashed v41 (S088), in the upgrade
database UPGRADE_DB (one per test run and worker, tests/db_names.py; a worker runs its files one
after another, so they do not collide).  The database keeps the parts line's CHECKs.  The
upgrade from v21 and the re-run went with S088 (§ 8.2).  Needs the dev MariaDB container.
"""

import pymysql
import pytest

from tests.migration_helpers import SQUASHED, _migrate, _recreate, _run



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


def test_the_checks_hold_in_the_database():
    """A number and its kind come together; a quantity is above 0 (the core refuses first; the
    database keeps the rule for any other writer)."""
    _recreate()
    _migrate(SQUASHED)
    _fill_one_ticket()
    _add_line("6205-2RS", "generic", "1.50")
    _add_line(None, None, "2")
    for part_number, number_kind, quantity in (("6205-2RS", None, "1"), (None, "maker", "1"),
                                               ("6205-2RS", "generic", "0")):
        with pytest.raises(pymysql.err.OperationalError) as refused:
            _add_line(part_number, number_kind, quantity)
        assert refused.value.args[0] == 4025      # ER_CONSTRAINT_FAILED
    assert [str(r["quantity"]) for r in _run("SELECT quantity FROM ticket_parts ORDER BY id")] == ["1.50", "2.00"]
