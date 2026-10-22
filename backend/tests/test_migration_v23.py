"""v23, work notes (S027 § 4, § 3 Tests), in the upgrade database vel_yantra_upgrade that the
v20-v22 migration tests also use (pytest runs the files one after another, so they do not
collide).  A v22 database with a ticket and its events gets ticket_events.updated_at/updated_by
(NULL on every existing row) and the ticket_note_edits table; a re-run changes nothing.  Needs the
dev MariaDB container.
"""

import local_db
from tests.test_migration_v20 import _migrate, _recreate, _run, _schema
from tests.test_migration_v22 import _fill_one_ticket

V22 = [m for m in local_db._MIGRATIONS if m[0] in (20, 21, 22)]
V23 = [m for m in local_db._MIGRATIONS if m[0] in (20, 21, 22, 23)]


def _versions():
    return [r["version"] for r in _run("SELECT version FROM db_version ORDER BY version")]


def _columns(table):
    return {r["COLUMN_NAME"]: (r["COLUMN_TYPE"], r["IS_NULLABLE"], r["COLUMN_DEFAULT"]) for r in _run(
        "SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT FROM information_schema.COLUMNS"
        " WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s", (table,))}


def _add_events():
    """A raised event and a remark-bearing move on the one ticket, as v22 stores them."""
    for event, remark in (("raised", None), ("acknowledged", "On my way")):
        _run("INSERT INTO ticket_events (ticket_id, event, occurred_at, remark, created_by)"
             " SELECT id, %s, '2026-10-21 09:05:00', %s, 'kla' FROM tickets", (event, remark))


def test_a_fresh_database_gets_v23():
    _recreate()
    _migrate(V23)
    assert _versions() == [20, 21, 22, 23]
    assert "ticket_note_edits" in {r["TABLE_NAME"] for r in _run(
        "SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE()")}
    assert {"updated_at", "updated_by"} <= set(_columns("ticket_events"))


def test_a_v22_database_with_events_gets_v23():
    _recreate()
    _migrate(V22)
    _fill_one_ticket()
    _add_events()
    events_before = _run("SELECT * FROM ticket_events ORDER BY id")

    _migrate(V23)
    assert _versions() == [20, 21, 22, 23]

    columns = _columns("ticket_events")
    assert columns["updated_at"] == ("datetime", "YES", "NULL")
    assert columns["updated_by"] == ("varchar(100)", "YES", "NULL")
    events_after = _run("SELECT * FROM ticket_events ORDER BY id")
    assert [{k: v for k, v in row.items() if k not in ("updated_at", "updated_by")} for row in events_after] == \
        list(events_before)
    assert all(row["updated_at"] is None and row["updated_by"] is None for row in events_after)

    assert _columns("ticket_note_edits") == {
        "id": ("int(11)", "NO", None),
        "event_id": ("int(11)", "NO", None),
        "remark": ("varchar(1000)", "NO", None),
        "replaced_at": ("datetime", "NO", "current_timestamp()"),
        "replaced_by": ("varchar(100)", "NO", None),
    }
    foreign_keys = {(r["CONSTRAINT_NAME"], r["COLUMN_NAME"], r["REFERENCED_TABLE_NAME"]) for r in _run(
        "SELECT CONSTRAINT_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME FROM information_schema.KEY_COLUMN_USAGE"
        " WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ticket_note_edits'"
        " AND REFERENCED_TABLE_NAME IS NOT NULL")}
    assert foreign_keys == {("fk_ticket_note_edits_event", "event_id", "ticket_events")}
    indexes = [(r["INDEX_NAME"], r["COLUMN_NAME"]) for r in _run(
        "SELECT INDEX_NAME, COLUMN_NAME FROM information_schema.STATISTICS WHERE TABLE_SCHEMA = DATABASE()"
        " AND TABLE_NAME = 'ticket_note_edits' AND INDEX_NAME LIKE 'ix_%%' ORDER BY SEQ_IN_INDEX")]
    assert indexes == [("ix_ticket_note_edits_event", "event_id"), ("ix_ticket_note_edits_event", "id")]
    # utf8mb4, so a Tamil note keeps its text
    collation = _run("SELECT TABLE_COLLATION FROM information_schema.TABLES"
                     " WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ticket_note_edits'")
    assert collation[0]["TABLE_COLLATION"].startswith("utf8mb4")

    # Re-run: v23 twice is a no-op
    schema = _schema()
    _run("DELETE FROM db_version WHERE version = 23")
    _migrate(V23)
    assert _versions() == [20, 21, 22, 23]
    assert _schema() == schema
