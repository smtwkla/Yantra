"""Migration v13: ticket work — cause, action, not a fault, repeat link on tickets; the
ticket_assignees and ticket_labour tables (S018 § 4).  On the test DB: db_version 13 is removed
and init_db runs twice; every statement is a no-op on re-run.  Needs the dev MariaDB container.
"""

import pymysql
import pytest

import config
from local_db import get_local_db, init_db


def _run(sql, params=()):
    conn = get_local_db(config.DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()
    finally:
        conn.close()


def _columns(table):
    return {r["COLUMN_NAME"]: (r["COLUMN_TYPE"], r["IS_NULLABLE"], r["COLUMN_DEFAULT"]) for r in _run(
        "SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s", (table,))}


def _indexes(table):
    rows = _run("SELECT INDEX_NAME, COLUMN_NAME FROM information_schema.STATISTICS WHERE TABLE_SCHEMA = DATABASE() "
                "AND TABLE_NAME = %s ORDER BY INDEX_NAME, SEQ_IN_INDEX", (table,))
    indexes = {}
    for r in rows:
        indexes.setdefault(r["INDEX_NAME"], []).append(r["COLUMN_NAME"])
    return indexes


def _foreign_keys(table):
    """Name -> (column, referenced table)."""
    return {r["CONSTRAINT_NAME"]: (r["COLUMN_NAME"], r["REFERENCED_TABLE_NAME"]) for r in _run(
        "SELECT CONSTRAINT_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME FROM information_schema.KEY_COLUMN_USAGE "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND REFERENCED_TABLE_NAME IS NOT NULL", (table,))}


def _checks(table):
    return {r["CONSTRAINT_NAME"] for r in _run(
        "SELECT CONSTRAINT_NAME FROM information_schema.CHECK_CONSTRAINTS "
        "WHERE CONSTRAINT_SCHEMA = DATABASE() AND TABLE_NAME = %s", (table,))}


def _shape():
    return tuple(f(table) for table in ("tickets", "ticket_assignees", "ticket_labour")
                 for f in (_columns, _indexes, _foreign_keys, _checks))


def test_ticket_columns_and_constraints():
    tickets = _columns("tickets")
    assert tickets["cause_id"][:2] == ("int(11)", "YES")
    assert tickets["action_id"][:2] == ("int(11)", "YES")
    assert tickets["not_a_fault"][:2] == ("tinyint(1)", "NO") and tickets["not_a_fault"][2] == "0"
    assert tickets["repeat_of_id"][:2] == ("int(11)", "YES")
    assert _indexes("tickets")["ix_tickets_repeat_of"] == ["repeat_of_id"]
    fks = _foreign_keys("tickets")
    assert fks["fk_tickets_cause"] == ("cause_id", "failure_causes")
    assert fks["fk_tickets_action"] == ("action_id", "maintenance_actions")
    assert fks["fk_tickets_repeat_of"] == ("repeat_of_id", "tickets")


def test_assignees_table():
    columns = _columns("ticket_assignees")
    assert set(columns) == {"ticket_id", "person_id", "assigned_at", "assigned_by"}
    assert _indexes("ticket_assignees")["PRIMARY"] == ["ticket_id", "person_id"]
    assert _foreign_keys("ticket_assignees") == {"fk_ticket_assignees_ticket": ("ticket_id", "tickets"),
                                                 "fk_ticket_assignees_person": ("person_id", "people")}


def test_labour_table():
    columns = _columns("ticket_labour")
    assert columns["trade_id"][:2] == ("int(11)", "YES")
    assert columns["work_date"][:2] == ("date", "NO")
    assert columns["minutes"][:2] == ("smallint(6)", "NO")
    assert {"created_at", "created_by", "updated_at", "updated_by"} <= set(columns)
    indexes = _indexes("ticket_labour")
    assert indexes["ix_ticket_labour_ticket"] == ["ticket_id"]
    assert indexes["ix_ticket_labour_person"] == ["person_id", "work_date"]
    assert _foreign_keys("ticket_labour") == {"fk_ticket_labour_ticket": ("ticket_id", "tickets"),
                                              "fk_ticket_labour_person": ("person_id", "people"),
                                              "fk_ticket_labour_trade": ("trade_id", "trades")}
    assert _checks("ticket_labour") == {"chk_ticket_labour_minutes"}


@pytest.mark.parametrize("minutes", [0, 1441])
def test_minutes_out_of_range_is_refused(make_equipment, make_ticket, make_person, minutes):
    ticket = make_ticket(make_equipment())
    person = make_person()
    with pytest.raises(pymysql.err.OperationalError) as caught:
        _run("INSERT INTO ticket_labour (ticket_id, person_id, work_date, minutes, created_by)"
             " VALUES (%s, %s, CURDATE(), %s, 'test')", (ticket["id"], person["id"], minutes))
    assert caught.value.args[0] == 4025


def test_rerun_changes_nothing():
    before = _shape()
    for _ in range(2):
        _run("DELETE FROM db_version WHERE version = 13")
        init_db(config.DB_CONFIG)
    assert _shape() == before
    assert _run("SELECT version FROM db_version WHERE version = 13")
