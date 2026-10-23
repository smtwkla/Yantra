"""v25, equipment lifecycle (S030 § 4.1, § 4.2, § 7.1), in the upgrade database UPGRADE_DB that
the v20-v24 migration tests also use (one per test run and worker, tests/db_names.py; a worker runs
its files one after another, so they do not collide).  A fresh database gets v25 with no refusal by
the precondition; a v24 database with equipment and a status event gets the column and the event
renamed, every value kept; a re-run (also a half-applied one) changes nothing; a hand-edited
equipment table with both columns or neither is refused unchanged.  Needs the dev MariaDB container.
"""

import pytest

import local_db
from local_db import MigrationBlocked
from tests.test_migration_v20 import _migrate, _recreate, _run, _schema
from tests.test_migration_v22 import _fill_one_ticket

V24 = [m for m in local_db._MIGRATIONS if m[0] in (20, 21, 22, 23, 24)]
V25 = [m for m in local_db._MIGRATIONS if m[0] in (20, 21, 22, 23, 24, 25)]

LIFECYCLE_TYPE = "enum('in_service','standby','out_of_use','scrapped')"
EVENT_TYPE = "enum('created','moved_unit','moved_parent','lifecycle','criticality','class','type','model')"


def _versions():
    return [r["version"] for r in _run("SELECT version FROM db_version ORDER BY version")]


def _column(table, name):
    rows = _run("SELECT ORDINAL_POSITION, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT FROM information_schema.COLUMNS"
                " WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s", (table, name))
    return rows[0] if rows else None


def _fill_equipment_and_history():
    """One machine in standby and its history as v24 stores it: created, then status."""
    _fill_one_ticket()
    _run("UPDATE equipment SET status = 'standby'")
    _run("INSERT INTO equipment_events (equipment_id, event, old_value, new_value, created_at, created_by)"
         " SELECT id, 'created', NULL, 'SMTW.MCC1.HP001', '2026-10-20 09:00:00', 'kla' FROM equipment")
    _run("INSERT INTO equipment_events (equipment_id, event, old_value, new_value, created_at, created_by)"
         " SELECT id, 'status', 'in_service', 'standby', '2026-10-21 10:30:00', 'ravi' FROM equipment")


def _events():
    return _run("SELECT * FROM equipment_events ORDER BY id")


def test_a_fresh_database_gets_v25():
    _recreate()
    _migrate(V25)   # the precondition passes while equipment does not exist yet (BR1-01)
    assert _versions() == [20, 21, 22, 23, 24, 25]
    assert _column("equipment", "status") is None
    lifecycle = _column("equipment", "lifecycle")
    assert (lifecycle["COLUMN_TYPE"], lifecycle["IS_NULLABLE"], lifecycle["COLUMN_DEFAULT"]) == (
        LIFECYCLE_TYPE, "NO", "'in_service'")
    event = _column("equipment_events", "event")
    assert (event["COLUMN_TYPE"], event["IS_NULLABLE"]) == (EVENT_TYPE, "NO")


def _migrated_v24_with_history():
    """A v24 database with equipment and history, taken to v25 → (equipment row and events before)."""
    _recreate()
    _migrate(V24)
    _fill_equipment_and_history()
    status_before = _column("equipment", "status")
    equipment_before = _run("SELECT * FROM equipment")
    events_before = _events()
    _migrate(V25)
    return status_before, equipment_before, events_before


def test_a_v24_database_with_equipment_and_history_gets_v25():
    status_before, equipment_before, events_before = _migrated_v24_with_history()
    assert _versions() == [20, 21, 22, 23, 24, 25]

    # The column keeps its type, default and place; only its name changes
    lifecycle = _column("equipment", "lifecycle")
    assert lifecycle == status_before
    assert _column("equipment", "status") is None
    equipment_after = _run("SELECT * FROM equipment")
    assert equipment_after[0]["lifecycle"] == "standby"
    renamed = [{("lifecycle" if k == "status" else k): v for k, v in row.items()} for row in equipment_before]
    assert equipment_after == renamed

    # The status event is now a lifecycle event; id, values, time and author are kept
    events_after = _events()
    assert [row["event"] for row in events_after] == ["created", "lifecycle"]
    assert events_after[0] == events_before[0]
    assert events_after[1] == {**events_before[1], "event": "lifecycle"}
    assert _column("equipment_events", "event")["COLUMN_TYPE"] == EVENT_TYPE


def test_a_rerun_changes_nothing():
    _migrated_v24_with_history()
    schema, equipment, events = _schema(), _run("SELECT * FROM equipment"), _events()

    # v25 run again in full
    _run("DELETE FROM db_version WHERE version = 25")
    _migrate(V25)
    assert _versions() == [20, 21, 22, 23, 24, 25]
    assert (_schema(), _run("SELECT * FROM equipment"), _events()) == (schema, equipment, events)

    # A half-applied v25: the rename ran, the event statements did not
    _recreate()
    _migrate(V24)
    _fill_equipment_and_history()
    _run(V25[-1][2][0])   # ALTER TABLE equipment RENAME COLUMN ...
    assert _column("equipment", "lifecycle") is not None
    _migrate(V25)
    assert _versions() == [20, 21, 22, 23, 24, 25]
    assert _schema() == schema
    assert [row["event"] for row in _events()] == ["created", "lifecycle"]


def _refused_unchanged(hand_edit, refusal):
    """A v24 database with history, hand-edited, is refused by v25 and left as it was."""
    _recreate()
    _migrate(V24)
    _fill_equipment_and_history()
    _run(hand_edit)
    schema, events = _schema(), _events()

    with pytest.raises(MigrationBlocked) as refused:
        _migrate(V25)
    assert str(refused.value) == refusal
    assert 25 not in _versions()
    assert _schema() == schema
    assert _events() == events


def test_both_columns_are_refused_unchanged():
    _refused_unchanged(
        "ALTER TABLE equipment ADD COLUMN lifecycle VARCHAR(20) NULL",
        "equipment has both status and lifecycle columns; drop the one that is not in use first — S030 § 4.2")


def test_neither_column_is_refused():
    _refused_unchanged("ALTER TABLE equipment DROP COLUMN status",
                       "equipment has neither a status nor a lifecycle column — S030 § 4.2")
