"""v38, countermeasures and their photos (S070 § 4.1, § 8.1), in the upgrade database UPGRADE_DB that the
v20-v37 migration tests also use (one per test run and worker, tests/db_names.py).  A fresh database gets
the table improvement_actions with its keys, CHECKs and foreign keys, and equipment_documents.action_id with
its key, foreign key and the widened owner CHECK; a v37 database with documents of all three owners keeps
every row; the CHECKs keep a done or cancelled row whole and a document to one owner; a re-run changes
nothing, and a half-applied v38 (the owner CHECK dropped, not added) adds it again.  Needs the dev MariaDB
container.
"""

import pymysql
import pytest

import local_db
from tests.test_migration_v20 import _migrate, _recreate, _run, _schema
from tests.test_migration_v22 import _fill_one_ticket
from tests.test_migration_v36 import _foreign_keys, _keys, _link, _one_improvement
from tests.test_migration_v37 import _add_why, _checks

V37 = [m for m in local_db._MIGRATIONS if m[0] in range(20, 38)]
V38 = [m for m in local_db._MIGRATIONS if m[0] in range(20, 39)]
VERSIONS = list(range(20, 39))

OLD_TABLES = ("equipment", "equipment_models", "tickets", "people", "improvements", "improvement_tickets",
              "improvement_whys")
ER_CONSTRAINT_FAILED = 4025


def _versions():
    return [r["version"] for r in _run("SELECT version FROM db_version ORDER BY version")]


def _old_rows():
    return {table: _run(f"SELECT * FROM {table}") for table in OLD_TABLES}


def _add_document(column, owner_id, name, action_id=None):
    """A document row of one owner (``column``), and optionally action_id too (two owners; v38 only)."""
    columns, values = [column], [owner_id]
    if action_id is not None:
        columns.append("action_id")
        values.append(action_id)
    _run(f"INSERT INTO equipment_documents ({', '.join(columns)}, kind, title, original_name, stored_name,"
         f" content_type, size_bytes, created_by) VALUES ({', '.join(['%s'] * len(values))}, 'photo', 'x', 'x.jpg',"
         " %s, 'image/jpeg', 1, 'kla')", (*values, name))


def _documents_of_three_owners():
    """A node's, a model's and a ticket's document, as production holds them."""
    node = _run("SELECT id, model_id FROM equipment")[0]
    ticket_id = _run("SELECT id FROM tickets")[0]["id"]
    _add_document("equipment_id", node["id"], "node.jpg")
    _add_document("model_id", node["model_id"], "model.jpg")
    _add_document("ticket_id", ticket_id, "ticket.jpg")


def _add_action(improvement_id, state="open", done=(None, None, None), cancelled=(None, None, None)):
    _run("INSERT INTO improvement_actions (improvement_id, kind, text, owner_id, due_date, state, done_text, done_at,"
         " done_by, cancel_reason, cancelled_at, cancelled_by, created_by)"
         " SELECT %s, 'corrective', 'Seal the panel', p.id, '2026-11-15', %s, %s, %s, %s, %s, %s, %s, 'kla'"
         " FROM people p ORDER BY p.id LIMIT 1", (improvement_id, state, *done, *cancelled))
    return _run("SELECT MAX(id) AS id FROM improvement_actions")[0]["id"]


def _owner_check_clause():
    return _run("SELECT CHECK_CLAUSE FROM information_schema.CHECK_CONSTRAINTS WHERE CONSTRAINT_SCHEMA = DATABASE()"
                " AND TABLE_NAME = 'equipment_documents' AND CONSTRAINT_NAME = 'chk_equipment_documents_owner'")


def _a_v37_database_with_rows():
    """v37 with a ticket, an improvement linked to it, a why and documents of all three owners -> the
    improvement's id."""
    _recreate()
    _migrate(V37)
    _fill_one_ticket()
    improvement_id = _one_improvement()
    _link(improvement_id, _run("SELECT id FROM tickets")[0]["id"], 1)
    _add_why(improvement_id, 1)
    _documents_of_three_owners()
    return improvement_id


def test_a_fresh_database_gets_v38():
    _recreate()
    _migrate(V38)
    assert _versions() == VERSIONS
    assert _run("SELECT COUNT(*) AS n FROM improvement_actions") == [{"n": 0}]
    assert _keys("improvement_actions") == [
        {"INDEX_NAME": "ix_improvement_actions_improvement", "NON_UNIQUE": 1, "cols": "improvement_id,id"},
        {"INDEX_NAME": "ix_improvement_actions_owner_state", "NON_UNIQUE": 1, "cols": "owner_id,state,due_date"},
        {"INDEX_NAME": "PRIMARY", "NON_UNIQUE": 0, "cols": "id"},
    ]
    assert _foreign_keys("improvement_actions") == [
        {"CONSTRAINT_NAME": "fk_improvement_actions_improvement", "REFERENCED_TABLE_NAME": "improvements"},
        {"CONSTRAINT_NAME": "fk_improvement_actions_owner", "REFERENCED_TABLE_NAME": "people"},
    ]
    assert _checks("improvement_actions") == [
        {"CONSTRAINT_NAME": "chk_improvement_actions_cancelled"}, {"CONSTRAINT_NAME": "chk_improvement_actions_done"}]
    assert _run("SELECT COLUMN_TYPE, COLUMN_DEFAULT FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE()"
                " AND TABLE_NAME = 'improvement_actions' AND COLUMN_NAME IN ('kind', 'state')"
                " ORDER BY ORDINAL_POSITION") == [
        {"COLUMN_TYPE": "enum('correction','corrective','preventive','design_out','lesson','spread')",
         "COLUMN_DEFAULT": None},
        {"COLUMN_TYPE": "enum('open','done','cancelled')", "COLUMN_DEFAULT": "'open'"},
    ]
    assert _run("SELECT COLUMN_NAME, IS_NULLABLE FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE()"
                " AND TABLE_NAME = 'equipment_documents' AND COLUMN_NAME IN ('ticket_id', 'action_id', 'kind')"
                " ORDER BY ORDINAL_POSITION") == [
        {"COLUMN_NAME": "ticket_id", "IS_NULLABLE": "YES"}, {"COLUMN_NAME": "action_id", "IS_NULLABLE": "YES"},
        {"COLUMN_NAME": "kind", "IS_NULLABLE": "NO"}]
    assert {"INDEX_NAME": "ix_equipment_documents_action", "NON_UNIQUE": 1, "cols": "action_id,removed_at"} in (
        _keys("equipment_documents"))
    assert {"CONSTRAINT_NAME": "fk_equipment_documents_action", "REFERENCED_TABLE_NAME": "improvement_actions"} in (
        _foreign_keys("equipment_documents"))
    assert "action_id" in _owner_check_clause()[0]["CHECK_CLAUSE"]


def test_a_v37_database_keeps_every_row():
    _a_v37_database_with_rows()
    before = _old_rows()
    documents_before = _run("SELECT * FROM equipment_documents ORDER BY id")
    _migrate(V38)
    assert _versions() == VERSIONS
    assert _old_rows() == before
    documents_after = _run("SELECT * FROM equipment_documents ORDER BY id")
    assert [{k: v for k, v in row.items() if k != "action_id"} for row in documents_after] == documents_before
    assert [row["action_id"] for row in documents_after] == [None, None, None]


def test_the_checks_keep_done_and_cancelled_whole():
    _recreate()
    _migrate(V38)
    _fill_one_ticket()
    improvement_id = _one_improvement()
    done = ("Fitted", "2026-10-30 10:00:00", "kla")
    cancelled = ("Duplicate", "2026-10-30 10:00:00", "kla")
    for state, done_fields, cancel_fields in (
            ("done", (None, "2026-10-30 10:00:00", "kla"), (None, None, None)),   # done without its text
            ("open", done, (None, None, None)),                                    # open with all three
            ("cancelled", (None, None, None), (None, "2026-10-30 10:00:00", "kla")),
            ("open", (None, None, None), cancelled)):
        with pytest.raises(pymysql.err.OperationalError) as refused:
            _add_action(improvement_id, state, done_fields, cancel_fields)
        assert refused.value.args[0] == ER_CONSTRAINT_FAILED
    _add_action(improvement_id)
    _add_action(improvement_id, "done", done)
    _add_action(improvement_id, "cancelled", cancelled=cancelled)
    assert [r["state"] for r in _run("SELECT state FROM improvement_actions ORDER BY id")] == [
        "open", "done", "cancelled"]


def test_a_document_has_exactly_one_of_four_owners():
    improvement_id = _a_v37_database_with_rows()
    _migrate(V38)
    action_id = _add_action(improvement_id)
    _run("INSERT INTO equipment_documents (action_id, kind, title, original_name, stored_name, content_type,"
         " size_bytes, created_by) VALUES (%s, 'photo', 'x', 'x.jpg', 'action.jpg', 'image/jpeg', 1, 'kla')",
         (action_id,))
    ticket_id = _run("SELECT id FROM tickets")[0]["id"]
    with pytest.raises(pymysql.err.OperationalError) as refused:
        _add_document("ticket_id", ticket_id, "two.jpg", action_id=action_id)
    assert refused.value.args[0] == ER_CONSTRAINT_FAILED
    assert "chk_equipment_documents_owner" in refused.value.args[1]


def test_a_rerun_changes_nothing():
    improvement_id = _a_v37_database_with_rows()
    _migrate(V38)
    _add_action(improvement_id)
    schema = _schema()
    kept = (_run("SELECT * FROM improvement_actions"), _run("SELECT * FROM equipment_documents ORDER BY id"))
    _run("DELETE FROM db_version WHERE version = 38")
    _migrate(V38)
    assert _schema() == schema
    assert (_run("SELECT * FROM improvement_actions"), _run("SELECT * FROM equipment_documents ORDER BY id")) == kept
    assert _versions() == VERSIONS


def test_a_half_applied_v38_adds_the_owner_check_again():
    _a_v37_database_with_rows()
    _migrate(V38)
    schema = _schema()
    _run("ALTER TABLE equipment_documents DROP CONSTRAINT chk_equipment_documents_owner")
    _run("DELETE FROM db_version WHERE version = 38")
    assert not _owner_check_clause()
    _migrate(V38)
    assert _schema() == schema
    assert _versions() == VERSIONS
