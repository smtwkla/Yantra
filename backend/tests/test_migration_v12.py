"""Tickets, ticket events, and ticket photos as a third owner of equipment_documents (S017 § 4)
— built by v12, now by v20 (S025: v1–v13 squashed; v20's re-run is test_migration_v20.py's).
Tests of today's schema.  Needs the dev MariaDB container.
"""

import pymysql
import pytest

import config
from local_db import get_local_db


def _run(sql, params=()):
    conn = get_local_db(config.DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()
    finally:
        conn.close()


def _columns(table):
    return {r["COLUMN_NAME"]: (r["COLUMN_TYPE"], r["IS_NULLABLE"]) for r in _run(
        "SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s", (table,))}


def _indexes(table):
    rows = _run("SELECT INDEX_NAME, COLUMN_NAME FROM information_schema.STATISTICS WHERE TABLE_SCHEMA = DATABASE() "
                "AND TABLE_NAME = %s ORDER BY INDEX_NAME, SEQ_IN_INDEX", (table,))
    indexes = {}
    for r in rows:
        indexes.setdefault(r["INDEX_NAME"], []).append(r["COLUMN_NAME"])
    return indexes


def _owner_checks():
    """The CHECK constraints on equipment_documents, by name -> clause."""
    return {r["CONSTRAINT_NAME"]: r["CHECK_CLAUSE"] for r in _run(
        "SELECT CONSTRAINT_NAME, CHECK_CLAUSE FROM information_schema.CHECK_CONSTRAINTS "
        "WHERE CONSTRAINT_SCHEMA = DATABASE() AND TABLE_NAME = 'equipment_documents'")}


def _insert_document(owners, name):
    equipment_id, model_id, ticket_id = owners
    _run("INSERT INTO equipment_documents (equipment_id, model_id, ticket_id, kind, title, original_name,"
         " stored_name, content_type, size_bytes, created_by) VALUES (%s, %s, %s, 'photo', 'x', 'x.jpg', %s,"
         " 'image/jpeg', 1, 'test')", (equipment_id, model_id, ticket_id, name))


def test_tables_and_indexes():
    tickets = _columns("tickets")
    assert tickets["serial"] == ("varchar(16)", "NO")
    assert tickets["component_id"] == ("int(11)", "YES")
    assert tickets["intensity"] == ("enum('critical','degraded','initial')", "NO")
    # 'scheduled' appended by v21 (S019 § 4.1)
    assert tickets["state"] == (
        "enum('raised','acknowledged','in_progress','back_in_service','closed','scheduled')", "NO")
    assert tickets["description"] == ("varchar(1000)", "YES")
    assert tickets["occurred_at"] == ("datetime", "NO")
    assert tickets["source"] == ("enum('manual')", "NO")
    assert {"created_at", "created_by", "updated_at", "updated_by"} <= set(tickets)
    events = _columns("ticket_events")
    assert events["event"] == ("varchar(30)", "NO") and events["intensity"][1] == "YES"
    assert events["person_id"] == ("int(11)", "YES")

    indexes = _indexes("tickets")
    assert indexes["uq_tickets_serial"] == ["serial"]
    assert indexes["ix_tickets_unit_state"] == ["unit_id", "state"]
    assert indexes["ix_tickets_equipment_state"] == ["equipment_id", "state"]
    assert indexes["ix_tickets_component_state"] == ["component_id", "state"]
    assert _indexes("ticket_events")["ix_ticket_events_ticket"] == ["ticket_id", "occurred_at", "id"]
    assert _indexes("equipment_documents")["ix_equipment_documents_ticket"] == ["ticket_id", "removed_at"]
    assert _columns("equipment_documents")["ticket_id"] == ("int(11)", "YES")


def test_the_owner_check_keeps_its_name_and_counts_three_owners():
    checks = _owner_checks()
    assert list(checks) == ["chk_equipment_documents_owner"]
    assert "ticket_id" in checks["chk_equipment_documents_owner"]


@pytest.mark.parametrize("which", ["equipment", "model", "ticket"])
def test_each_single_owner_is_accepted(make_equipment, make_model, make_ticket, uniq, which):
    node = make_equipment()
    owners = {"equipment": (node["id"], None, None), "model": (None, make_model()["id"], None),
              "ticket": (None, None, make_ticket(node)["id"])}[which]
    name = f"v12-{uniq.username()}.jpg"
    _insert_document(owners, name)
    _run("DELETE FROM equipment_documents WHERE stored_name = %s", (name,))


@pytest.mark.parametrize("owners", ["none", "equipment+ticket", "model+ticket"])
def test_none_or_two_owners_are_refused(make_equipment, make_model, make_ticket, uniq, owners):
    node = make_equipment()
    ticket_id = make_ticket(node)["id"]
    values = {"none": (None, None, None), "equipment+ticket": (node["id"], None, ticket_id),
              "model+ticket": (None, make_model()["id"], ticket_id)}[owners]
    with pytest.raises(pymysql.err.OperationalError) as caught:
        _insert_document(values, f"v12-{uniq.username()}.jpg")
    assert caught.value.args[0] == 4025
