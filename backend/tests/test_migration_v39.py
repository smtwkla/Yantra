"""v39, the states, the timeline and the verified close (S072 § 4.1, § 8.1), in the upgrade database UPGRADE_DB
that the v20-v38 migration tests also use (one per test run and worker, tests/db_names.py).  A fresh database
gets improvement_events with its key and three foreign keys, and improvements its six columns, the unique key,
the foreign key, four CHECKs and the six-value state ENUM; a v38 database with rows of S067-S070's shape keeps
every row, gets the states the rows earn and the backfilled timeline lines; the CHECKs keep the watch, the
close and the follow-up whole; a re-run changes nothing and doubles no line.  Needs the dev MariaDB container.
"""

from datetime import datetime

import pymysql
import pytest

import local_db
from tests.test_migration_v20 import _migrate, _recreate, _run, _schema
from tests.test_migration_v22 import _fill_one_ticket
from tests.test_migration_v36 import _foreign_keys, _keys, _link, _one_improvement
from tests.test_migration_v37 import _add_why, _cause_id, _checks, _set_root_cause
from tests.test_migration_v38 import _add_action

V38 = [m for m in local_db._MIGRATIONS if m[0] in range(20, 39)]
V39 = [m for m in local_db._MIGRATIONS if m[0] in range(20, 40)]
VERSIONS = list(range(20, 40))

OLD_TABLES = ("tickets", "people", "improvement_tickets", "improvement_whys", "improvement_actions")
NEW_COLUMNS = ("watch_days", "watch_from", "closed_at", "closed_by", "close_remark", "follow_up_of_id")
ER_DUP_ENTRY = 1062
ER_CONSTRAINT_FAILED = 4025
DONE = ("Fitted the sealed block", "2026-10-28 11:00:00", "kannan")
CANCELLED = ("Duplicate", "2026-10-29 09:30:00", "ravi")


def _versions():
    return [r["version"] for r in _run("SELECT version FROM db_version ORDER BY version")]


def _old_rows():
    return {table: _run(f"SELECT * FROM {table}") for table in OLD_TABLES}


def _another_improvement(serial):
    """A copy of the first improvement under another serial -> its id."""
    _run("INSERT INTO improvements (serial, unit_id, equipment_id, title, problem, lead_id, created_by)"
         " SELECT %s, unit_id, equipment_id, title, problem, lead_id, 'ravi' FROM improvements"
         " WHERE serial = 'IM-2026-10-001'", (serial,))
    return _run("SELECT id FROM improvements WHERE serial = %s", (serial,))[0]["id"]


def _a_v38_database_with_rows():
    """A: only a ticket; B: a root cause, an open countermeasure and two whys; C: a root cause, one done and one
    cancelled countermeasure; D: no root cause and one done countermeasure -> ``{name: id}``."""
    _recreate()
    _migrate(V38)
    _fill_one_ticket()
    ids = {"A": _one_improvement()}
    for name, number in (("B", 2), ("C", 3), ("D", 4)):
        ids[name] = _another_improvement(f"IM-2026-10-00{number}")
    _link(ids["A"], _run("SELECT id FROM tickets")[0]["id"], 1)
    cause = _cause_id("5.1")
    for name in ("B", "C"):
        _set_root_cause(ids[name], "No cleaning standard", cause)
    _add_why(ids["B"], 1)
    _run("INSERT INTO improvement_whys (improvement_id, position, question, answer, evidence, created_by)"
         " VALUES (%s, 2, 'Why is the seal torn?', 'Old', 'Photo', 'kla')", (ids["B"],))
    _add_action(ids["B"])
    _add_action(ids["C"], "done", DONE)
    _add_action(ids["C"], "cancelled", cancelled=CANCELLED)
    _add_action(ids["D"], "done", DONE)
    return ids


def _lines(improvement_id):
    return _run("SELECT event, occurred_at, ticket_id, action_id, remark, earlier, created_by FROM improvement_events"
                " WHERE improvement_id = %s ORDER BY id", (improvement_id,))


def test_a_fresh_database_gets_v39():
    _recreate()
    _migrate(V39)
    assert _versions() == VERSIONS
    assert _run("SELECT COUNT(*) AS n FROM improvement_events") == [{"n": 0}]
    assert _keys("improvement_events") == [
        {"INDEX_NAME": "fk_improvement_events_action", "NON_UNIQUE": 1, "cols": "action_id"},
        {"INDEX_NAME": "fk_improvement_events_ticket", "NON_UNIQUE": 1, "cols": "ticket_id"},
        {"INDEX_NAME": "ix_improvement_events_improvement", "NON_UNIQUE": 1, "cols": "improvement_id,occurred_at,id"},
        {"INDEX_NAME": "PRIMARY", "NON_UNIQUE": 0, "cols": "id"},
    ]
    assert _foreign_keys("improvement_events") == [
        {"CONSTRAINT_NAME": "fk_improvement_events_action", "REFERENCED_TABLE_NAME": "improvement_actions"},
        {"CONSTRAINT_NAME": "fk_improvement_events_improvement", "REFERENCED_TABLE_NAME": "improvements"},
        {"CONSTRAINT_NAME": "fk_improvement_events_ticket", "REFERENCED_TABLE_NAME": "tickets"},
    ]
    columns = _run("SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT FROM information_schema.COLUMNS"
                   " WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'improvements' ORDER BY ORDINAL_POSITION")
    by_name = {c["COLUMN_NAME"]: c for c in columns}
    names = [c["COLUMN_NAME"] for c in columns]
    assert names[names.index("contributing_causes") + 1:][:6] == list(NEW_COLUMNS)
    assert (by_name["watch_days"]["COLUMN_TYPE"], by_name["watch_days"]["IS_NULLABLE"],
            by_name["watch_days"]["COLUMN_DEFAULT"]) == ("smallint(6)", "NO", "90")
    assert all(by_name[c]["IS_NULLABLE"] == "YES" for c in NEW_COLUMNS[1:])
    assert (by_name["state"]["COLUMN_TYPE"], by_name["state"]["COLUMN_DEFAULT"]) == (
        "enum('analysing','actions_open','watching','closed_effective','closed_not_effective','dropped')",
        "'analysing'")
    assert {"INDEX_NAME": "uq_improvements_follow_up", "NON_UNIQUE": 0, "cols": "follow_up_of_id"} in (
        _keys("improvements"))
    assert {"CONSTRAINT_NAME": "fk_improvements_follow_up", "REFERENCED_TABLE_NAME": "improvements"} in (
        _foreign_keys("improvements"))
    assert {c["CONSTRAINT_NAME"] for c in _checks("improvements")} >= {
        "chk_improvements_watch_days", "chk_improvements_watch_from", "chk_improvements_closed",
        "chk_improvements_close_remark"}


def test_a_v38_database_keeps_every_row_and_gets_its_states_and_lines():
    ids = _a_v38_database_with_rows()
    before = _old_rows()
    improvements_before = {r["id"]: r for r in _run("SELECT * FROM improvements")}
    _migrate(V39)
    assert _versions() == VERSIONS
    assert _old_rows() == before
    after = {r["id"]: r for r in _run("SELECT * FROM improvements")}
    for improvement_id, row in improvements_before.items():
        kept = {k: v for k, v in after[improvement_id].items() if k not in (*NEW_COLUMNS, "state")}
        assert kept == {k: v for k, v in row.items() if k != "state"}
    assert {name: (after[i]["state"], after[i]["watch_from"]) for name, i in ids.items()} == {
        "A": ("analysing", None), "B": ("actions_open", None),
        "C": ("watching", datetime(2026, 10, 28, 11, 0)), "D": ("analysing", None)}
    assert {after[i]["watch_days"] for i in ids.values()} == {90}

    a_row = improvements_before[ids["A"]]
    link = _run("SELECT * FROM improvement_tickets")[0]
    assert _lines(ids["A"]) == [
        {"event": "started", "occurred_at": a_row["created_at"], "ticket_id": None, "action_id": None, "remark": None,
         "earlier": None, "created_by": "kla"},
        {"event": "ticket_linked", "occurred_at": link["created_at"], "ticket_id": link["ticket_id"], "action_id": None,
         "remark": None, "earlier": None, "created_by": "kla"},
    ]
    cause = _run("SELECT code, label FROM failure_causes WHERE code = '5.1'")[0]
    b_lines = _lines(ids["B"])
    assert [line["event"] for line in b_lines] == ["started", "why_added", "why_added", "root_cause_set",
                                                   "action_added"]
    assert [line["remark"] for line in b_lines[1:3]] == [
        "1. Why? Because: Because", "2. Why is the seal torn? Because: Old Evidence: Photo"]
    b_row = improvements_before[ids["B"]]
    assert b_lines[3]["remark"] == f"{cause['code']} {cause['label']}: No cleaning standard"
    assert (b_lines[3]["occurred_at"], b_lines[3]["created_by"]) == (
        b_row["updated_at"] or b_row["created_at"], b_row["updated_by"] or "ravi")
    assert b_lines[4]["remark"] == "Seal the panel" and b_lines[4]["action_id"] is not None
    c_lines = _lines(ids["C"])
    assert [(line["event"], line["remark"], line["created_by"]) for line in c_lines[2:]] == [
        ("action_added", "Seal the panel", "kla"), ("action_added", "Seal the panel", "kla"),
        ("action_done", "Fitted the sealed block", "kannan"), ("action_cancelled", "Duplicate", "ravi")]
    assert [line["occurred_at"] for line in c_lines[4:]] == [datetime(2026, 10, 28, 11, 0),
                                                             datetime(2026, 10, 29, 9, 30)]
    assert [line["event"] for line in _lines(ids["D"])] == ["started", "action_added", "action_done"]
    assert _run("SELECT COUNT(*) AS n FROM improvement_events WHERE event = 'state_changed'") == [{"n": 0}]


@pytest.mark.parametrize("assignment, params", [
    ("watch_days = 29", ()),
    ("watch_days = 366", ()),
    ("state = 'watching'", ()),                                                    # watch_from NULL
    ("state = 'closed_effective', watch_from = NOW()", ()),                        # no closed_at
    ("state = 'dropped', closed_at = NOW(), closed_by = 'kla'", ()),               # no close_remark
    ("state = 'analysing', watch_from = NOW()", ()),
])
def test_the_checks(assignment, params):
    _recreate()
    _migrate(V39)
    _fill_one_ticket()
    improvement_id = _one_improvement()
    with pytest.raises(pymysql.err.OperationalError) as refused:
        _run(f"UPDATE improvements SET {assignment} WHERE id = %s", (*params, improvement_id))
    assert refused.value.args[0] == ER_CONSTRAINT_FAILED


def test_a_dropped_row_and_one_follow_up_per_improvement():
    _recreate()
    _migrate(V39)
    _fill_one_ticket()
    first = _one_improvement()
    _run("UPDATE improvements SET state = 'dropped', closed_at = NOW(), closed_by = 'kla', close_remark = 'No cause'"
         " WHERE id = %s", (first,))
    second = _another_improvement("IM-2026-10-002")
    third = _another_improvement("IM-2026-10-003")
    _run("UPDATE improvements SET follow_up_of_id = %s WHERE id = %s", (first, second))
    with pytest.raises(pymysql.err.IntegrityError) as refused:
        _run("UPDATE improvements SET follow_up_of_id = %s WHERE id = %s", (first, third))
    assert refused.value.args[0] == ER_DUP_ENTRY


def test_a_rerun_changes_nothing_and_doubles_no_line():
    _a_v38_database_with_rows()
    _migrate(V39)
    schema = _schema()
    kept = (_run("SELECT * FROM improvements ORDER BY id"), _run("SELECT * FROM improvement_events ORDER BY id"))
    _run("DELETE FROM db_version WHERE version = 39")
    _migrate(V39)
    assert _schema() == schema
    assert (_run("SELECT * FROM improvements ORDER BY id"), _run("SELECT * FROM improvement_events ORDER BY id")) == kept
    assert _versions() == VERSIONS
