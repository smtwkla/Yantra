"""v21, deferred work (S019 § 4, § 8), in the upgrade database vel_yantra_upgrade that
test_migration_v20.py also uses (pytest runs the files one after another, so they do not
collide).  A v20 database holding a ticket gets v21: the row is unchanged, the new columns are
NULL, the state ENUM has 'scheduled' appended and keeps NOT NULL DEFAULT 'raised', and
chk_tickets_plan holds; a re-run changes nothing.  Needs the dev MariaDB container.
"""

import local_db
from tests.test_migration_v20 import _migrate, _recreate, _run, _schema
from tickets_core import WAITING_REASONS

V20 = [m for m in local_db._MIGRATIONS if m[0] == 20]
V21 = [m for m in local_db._MIGRATIONS if m[0] in (20, 21)]
REASONS = "enum(" + ",".join(f"'{code}'" for code in WAITING_REASONS) + ")"


def _fill_one_ticket():
    """The shortest chain a ticket needs, with its raised event (S019 BS1-02)."""
    _run("INSERT INTO sites (code, name, created_by) VALUES ('SMTW', 'SMTW plant', 'kla')")
    _run("INSERT INTO units (site_id, code, name, created_by) SELECT id, 'MCC1', 'MCC1', 'kla' FROM sites")
    _run("INSERT INTO equipment_classes (code, name, created_by) VALUES ('HP', 'Hydraulic press', 'kla')")
    _run("INSERT INTO manufacturers (name, created_by) VALUES ('Generic', 'kla')")
    _run("INSERT INTO equipment_models (manufacturer_id, designation, class_id, created_by)"
         " SELECT m.id, 'HP-1', c.id, 'kla' FROM manufacturers m, equipment_classes c")
    _run("INSERT INTO equipment (code, level, unit_id, class_id, model_id, name, created_by)"
         " SELECT 'HP001', 'equipment', u.id, m.class_id, m.id, 'Press', 'kla' FROM units u, equipment_models m")
    _run("INSERT INTO tickets (serial, equipment_id, unit_id, intensity, state, description, occurred_at, created_by)"
         " SELECT 'TK-2026-10-001', e.id, e.unit_id, 'critical', 'acknowledged', 'Stopped', '2026-10-21 09:00:00',"
         " 'kla' FROM equipment e")
    _run("INSERT INTO ticket_events (ticket_id, event, to_state, occurred_at, intensity, created_by)"
         " SELECT id, 'raised', 'raised', occurred_at, 'critical', 'kla' FROM tickets")


def _columns(table):
    return {r["COLUMN_NAME"]: (r["COLUMN_TYPE"], r["IS_NULLABLE"], r["COLUMN_DEFAULT"]) for r in _run(
        "SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT FROM information_schema.COLUMNS"
        " WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s", (table,))}


def _versions():
    return [r["version"] for r in _run("SELECT version FROM db_version ORDER BY version")]


def test_a_v20_database_with_a_ticket_gets_v21():
    _recreate()
    _migrate(V20)
    _fill_one_ticket()
    before = {table: _run(f"SELECT * FROM {table}") for table in ("tickets", "ticket_events")}

    _migrate(V21)
    assert _versions() == [20, 21]
    for table, rows in before.items():
        after = _run(f"SELECT * FROM {table}")
        assert [{k: row[k] for k in rows[0]} for row in after] == rows, table
    ticket = _run("SELECT planned_date, waiting_reason FROM tickets")[0]
    assert ticket == {"planned_date": None, "waiting_reason": None}
    event = _run("SELECT planned_date, waiting_reason, machine_stopped FROM ticket_events")[0]
    assert event == {"planned_date": None, "waiting_reason": None, "machine_stopped": None}

    tickets = _columns("tickets")
    assert tickets["state"] == (
        "enum('raised','acknowledged','in_progress','back_in_service','closed','scheduled')", "NO", "'raised'")
    # The ENUM is the core's six codes, in its order (WAITING_REASONS)
    assert tickets["planned_date"] == ("date", "YES", "NULL")
    assert tickets["waiting_reason"] == (REASONS, "YES", "NULL")
    events = _columns("ticket_events")
    assert events["planned_date"] == ("date", "YES", "NULL")
    assert events["waiting_reason"] == (REASONS, "YES", "NULL")
    assert events["machine_stopped"] == ("tinyint(1)", "YES", "NULL")
    checks = {r["CONSTRAINT_NAME"]: r["CHECK_CLAUSE"] for r in _run(
        "SELECT CONSTRAINT_NAME, CHECK_CLAUSE FROM information_schema.CHECK_CONSTRAINTS"
        " WHERE CONSTRAINT_SCHEMA = DATABASE() AND TABLE_NAME = 'tickets'")}
    assert "chk_tickets_plan" in checks

    # Re-run: v21 twice is a no-op
    schema = _schema()
    _run("DELETE FROM db_version WHERE version = 21")
    _migrate(V21)
    assert _versions() == [20, 21]
    assert _schema() == schema
