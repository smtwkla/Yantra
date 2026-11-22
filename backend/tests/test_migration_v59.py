"""v59, tasks on a ticket (S106 § 4.1, § 8.1), in the upgrade database UPGRADE_DB (one per test run and worker,
tests/db_names.py), dropped and created by these tests.

- a fresh build: ticket_tasks with its two keys, two foreign keys and two CHECKs; ticket_events.task_id with its
  key and foreign key;
- a database at v58 with a ticket and its events (built from the migrations up to 58; v58's text is in
  local_db._MIGRATIONS, never edited, so no frozen fixture is needed): v59 keeps every row, task_id is NULL on
  each, db_version gains 59;
- the CHECKs refuse a done task without its done fields, an open one with them, and the same for cancelled; an
  event naming an unknown task is refused;
- a re-run changes nothing, and a half-applied v59 (the table made, the ALTER not run) re-runs to the fresh shape.

Needs the dev MariaDB container.
"""

import pymysql
import pytest

import local_db
from tests.migration_helpers import _migrate, _recreate, _run, _schema, _versions
from tests.test_migration_v22 import _fill_one_ticket
from tests.test_migration_v36 import _foreign_keys, _keys

V58 = [m for m in local_db._MIGRATIONS if m[0] <= 58]
V59 = [m for m in local_db._MIGRATIONS if m[0] <= 59]
(_, _, V59_STATEMENTS), = [m for m in local_db._MIGRATIONS if m[0] == 59]

ER_CONSTRAINT_FAILED = 4025
ER_NO_REFERENCED_ROW = 1452

DONE_FIELDS = {"done_text": "Fuse replaced", "done_at": "2026-11-22 10:00:00", "done_by": "kla"}
CANCEL_FIELDS = {"cancel_reason": "Moved to the improvement", "cancelled_at": "2026-11-22 10:00:00",
                 "cancelled_by": "kla"}


def _insert(table, row):
    _run(f"INSERT INTO {table} ({', '.join(row)}) VALUES ({', '.join(['%s'] * len(row))})", list(row.values()))
    return _run(f"SELECT MAX(id) AS id FROM {table}")[0]["id"]


def _refused(code, table, row):
    with pytest.raises((pymysql.err.OperationalError, pymysql.err.IntegrityError)) as refused:
        _insert(table, row)
    assert refused.value.args[0] == code, refused.value


def _columns(table):
    return [r["COLUMN_NAME"] for r in _run("SELECT COLUMN_NAME FROM information_schema.COLUMNS"
                                           " WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s"
                                           " ORDER BY ORDINAL_POSITION", (table,))]


def _checks(table):
    return {r["CONSTRAINT_NAME"] for r in _run("SELECT CONSTRAINT_NAME FROM information_schema.CHECK_CONSTRAINTS"
                                               " WHERE CONSTRAINT_SCHEMA = DATABASE() AND TABLE_NAME = %s",
                                               (table,))}


def _task_row(**overrides):
    """A task on the one ticket of _fill_one_ticket, owned by a person made here."""
    owner = _insert("people", {"name": "Owner", "employment": "direct", "created_by": "kla"})
    ticket = _run("SELECT id FROM tickets")[0]["id"]
    return {"ticket_id": ticket, "text": "Check the heater", "owner_id": owner, "due_date": "2026-11-25",
            "created_by": "kla", **overrides}


def _add_events():
    """Two lines on the ticket of _fill_one_ticket: its raise and a note."""
    for event, remark in (("raised", None), ("note", "Moisture in the panel")):
        _run("INSERT INTO ticket_events (ticket_id, event, to_state, occurred_at, remark, created_by)"
             " SELECT id, %s, NULL, '2026-10-21 09:00:00', %s, 'kla' FROM tickets", (event, remark))


@pytest.fixture(scope="module")
def fresh():
    _recreate()
    _migrate(V59)
    _fill_one_ticket()
    return _schema()


def test_the_tasks_table(fresh):
    keys = {k["INDEX_NAME"]: k["cols"] for k in _keys("ticket_tasks")}
    assert keys["ix_ticket_tasks_ticket"] == "ticket_id,id"
    assert keys["ix_ticket_tasks_owner_state"] == "owner_id,state,due_date"
    assert [(f["CONSTRAINT_NAME"], f["REFERENCED_TABLE_NAME"]) for f in _foreign_keys("ticket_tasks")] == [
        ("fk_ticket_tasks_owner", "people"), ("fk_ticket_tasks_ticket", "tickets")]
    assert _checks("ticket_tasks") == {"chk_ticket_tasks_done", "chk_ticket_tasks_cancelled"}
    assert _columns("ticket_tasks") == [
        "id", "ticket_id", "text", "owner_id", "due_date", "state", "done_text", "done_at", "done_by",
        "cancel_reason", "cancelled_at", "cancelled_by", "created_at", "created_by", "updated_at", "updated_by"]


def test_the_events_task_column(fresh):
    columns = _columns("ticket_events")
    assert columns[columns.index("machine_stopped") + 1] == "task_id"
    assert {k["INDEX_NAME"]: k["cols"] for k in _keys("ticket_events")}["ix_ticket_events_task"] == "task_id"
    assert ("fk_ticket_events_task", "ticket_tasks") in [
        (f["CONSTRAINT_NAME"], f["REFERENCED_TABLE_NAME"]) for f in _foreign_keys("ticket_events")]


def test_the_checks(fresh):
    _refused(ER_CONSTRAINT_FAILED, "ticket_tasks", _task_row(state="done"))
    _refused(ER_CONSTRAINT_FAILED, "ticket_tasks", _task_row(state="done", **{**DONE_FIELDS, "done_text": None}))
    _refused(ER_CONSTRAINT_FAILED, "ticket_tasks", _task_row(**DONE_FIELDS))
    _refused(ER_CONSTRAINT_FAILED, "ticket_tasks", _task_row(state="cancelled"))
    _refused(ER_CONSTRAINT_FAILED, "ticket_tasks", _task_row(**CANCEL_FIELDS))
    _insert("ticket_tasks", _task_row())
    _insert("ticket_tasks", _task_row(state="done", **DONE_FIELDS))
    _insert("ticket_tasks", _task_row(state="cancelled", **CANCEL_FIELDS))


def test_an_event_naming_an_unknown_task_is_refused(fresh):
    ticket = _run("SELECT id FROM tickets")[0]["id"]
    event = {"ticket_id": ticket, "event": "task_done", "occurred_at": "2026-11-22 10:00:00", "created_by": "kla"}
    _refused(ER_NO_REFERENCED_ROW, "ticket_events", {**event, "task_id": 999999})
    task = _insert("ticket_tasks", _task_row())
    _insert("ticket_events", {**event, "task_id": task})


def test_a_v58_database_with_a_ticket_and_its_events_migrates(fresh):
    _recreate()
    _migrate(V58)
    _fill_one_ticket()
    _add_events()
    before = _run("SELECT * FROM ticket_events ORDER BY id")
    assert _versions()[-1] == 58
    _migrate(V59)
    assert _versions()[-2:] == [58, 59]
    after = _run("SELECT * FROM ticket_events ORDER BY id")
    assert len(after) == len(before) == 2
    for old, new in zip(before, after):
        assert new.pop("task_id") is None
        assert new == old
    _run("DELETE FROM ticket_events")
    assert _schema() == fresh


def test_a_re_run_and_a_half_applied_v59(fresh):
    _recreate()
    _migrate(V59)
    _fill_one_ticket()
    for statement in V59_STATEMENTS:            # every statement is safe to run twice
        _run(statement)
    assert _schema() == fresh
    _recreate()
    _migrate(V58)
    _fill_one_ticket()
    _run(V59_STATEMENTS[0])                     # the table made, the ALTER not run
    _migrate(V59)
    assert _versions()[-1] == 59
    assert _schema() == fresh
