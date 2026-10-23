"""v26, indexes for the Me page (S031 § 4), in the upgrade database UPGRADE_DB that the v20-v25
migration tests also use (one per test run and worker, tests/db_names.py).  A fresh database gets
both indexes in the stated column order; a v25 database with a ticket and events gets them and
keeps every row; a re-run changes nothing.  Needs the dev MariaDB container.
"""

import local_db
from tests.test_migration_v20 import _migrate, _recreate, _run, _schema
from tests.test_migration_v22 import _fill_one_ticket

V25 = [m for m in local_db._MIGRATIONS if m[0] in (20, 21, 22, 23, 24, 25)]
V26 = [m for m in local_db._MIGRATIONS if m[0] in (20, 21, 22, 23, 24, 25, 26)]


def _versions():
    return [r["version"] for r in _run("SELECT version FROM db_version ORDER BY version")]


def _index(table, name):
    """The index's columns in order, or None."""
    rows = _run("SELECT COLUMN_NAME FROM information_schema.STATISTICS WHERE TABLE_SCHEMA = DATABASE()"
                " AND TABLE_NAME = %s AND INDEX_NAME = %s ORDER BY SEQ_IN_INDEX", (table, name))
    return [r["COLUMN_NAME"] for r in rows] or None


def _assert_indexes():
    assert _index("ticket_events", "ix_ticket_events_created_by") == ["created_by", "created_at", "id"]
    assert _index("tickets", "ix_tickets_created_by") == ["created_by"]


def test_a_fresh_database_gets_v26():
    _recreate()
    _migrate(V26)
    assert _versions() == [20, 21, 22, 23, 24, 25, 26]
    _assert_indexes()


def test_a_v25_database_gets_v26_and_keeps_its_rows():
    _recreate()
    _migrate(V25)
    _fill_one_ticket()
    _run("INSERT INTO ticket_events (ticket_id, event, to_state, occurred_at, created_by)"
         " SELECT id, 'raised', 'raised', '2026-10-21 09:00:00', 'kla' FROM tickets")
    before = {table: _run(f"SELECT * FROM {table} ORDER BY id") for table in ("tickets", "ticket_events")}
    assert _index("tickets", "ix_tickets_created_by") is None

    _migrate(V26)
    assert _versions() == [20, 21, 22, 23, 24, 25, 26]
    assert {table: _run(f"SELECT * FROM {table} ORDER BY id") for table in ("tickets", "ticket_events")} == before
    _assert_indexes()


def test_running_v26_again_changes_nothing():
    _recreate()
    _migrate(V26)
    schema = _schema()
    _run("DELETE FROM db_version WHERE version = 26")
    _migrate(V26)
    assert _versions() == [20, 21, 22, 23, 24, 25, 26]
    assert _schema() == schema
