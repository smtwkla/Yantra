"""v41, one-point lessons and their photos (S075 § 4.1, § 8.1), in the upgrade database UPGRADE_DB that the
v20-v40 migration tests also use (one per test run and worker, tests/db_names.py).  A fresh database gets the
table procedures with its keys, unique keys and foreign keys, and equipment_documents.procedure_id with its key,
foreign key and the owner CHECK widened to five owners; a v40 database with documents of all four owners keeps
every row; the CHECK keeps a document to one owner; one lesson per countermeasure; Tamil text is stored whole;
a re-run changes nothing, and a half-applied v41 (the owner CHECK dropped, not added) adds it again.  Needs the
dev MariaDB container.
"""

import pymysql
import pytest

import local_db
from tests.test_migration_v20 import _migrate, _recreate, _run, _schema
from tests.test_migration_v22 import _fill_one_ticket
from tests.test_migration_v36 import _foreign_keys, _keys, _one_improvement
from tests.test_migration_v38 import _add_action, _add_document, _documents_of_three_owners, _owner_check_clause

V40 = [m for m in local_db._MIGRATIONS if m[0] in range(20, 41)]
V41 = [m for m in local_db._MIGRATIONS if m[0] in range(20, 42)]
VERSIONS = list(range(20, 42))

ER_CONSTRAINT_FAILED = 4025
ER_DUP_ENTRY = 1062


def _versions():
    return [r["version"] for r in _run("SELECT version FROM db_version ORDER BY version")]


def _add_lesson(serial, action_id=None, title="Keep the panel door shut", body="Dust trips the contactor"):
    """A lesson on the one machine, for its class -> its id."""
    _run("INSERT INTO procedures (serial, equipment_id, class_id, title, body, action_id, created_by)"
         " SELECT %s, e.id, e.class_id, %s, %s, %s, 'kla' FROM equipment e ORDER BY e.id LIMIT 1",
         (serial, title, body, action_id))
    return _run("SELECT id FROM procedures WHERE serial = %s", (serial,))[0]["id"]


def _a_v40_database_with_rows():
    """v40 with a ticket, an improvement, a countermeasure and documents of all four owners -> the
    countermeasure's id."""
    _recreate()
    _migrate(V40)
    _fill_one_ticket()
    action_id = _add_action(_one_improvement())
    _documents_of_three_owners()
    _add_document("action_id", action_id, "action.jpg")
    return action_id


def test_a_fresh_database_gets_v41():
    _recreate()
    _migrate(V41)
    assert _versions() == VERSIONS
    assert _run("SELECT COUNT(*) AS n FROM procedures") == [{"n": 0}]
    assert _keys("procedures") == [
        {"INDEX_NAME": "ix_procedures_class", "NON_UNIQUE": 1, "cols": "class_id,active"},
        {"INDEX_NAME": "ix_procedures_equipment", "NON_UNIQUE": 1, "cols": "equipment_id,active"},
        {"INDEX_NAME": "PRIMARY", "NON_UNIQUE": 0, "cols": "id"},
        {"INDEX_NAME": "uq_procedures_action", "NON_UNIQUE": 0, "cols": "action_id"},
        {"INDEX_NAME": "uq_procedures_serial", "NON_UNIQUE": 0, "cols": "serial"},
    ]
    assert _foreign_keys("procedures") == [
        {"CONSTRAINT_NAME": "fk_procedures_action", "REFERENCED_TABLE_NAME": "improvement_actions"},
        {"CONSTRAINT_NAME": "fk_procedures_class", "REFERENCED_TABLE_NAME": "equipment_classes"},
        {"CONSTRAINT_NAME": "fk_procedures_equipment", "REFERENCED_TABLE_NAME": "equipment"},
    ]
    assert _run("SELECT COLUMN_TYPE, COLUMN_DEFAULT FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE()"
                " AND TABLE_NAME = 'procedures' AND COLUMN_NAME IN ('kind', 'active') ORDER BY ORDINAL_POSITION") == [
        {"COLUMN_TYPE": "enum('one_point_lesson')", "COLUMN_DEFAULT": "'one_point_lesson'"},
        {"COLUMN_TYPE": "tinyint(1)", "COLUMN_DEFAULT": "1"},
    ]
    assert _run("SELECT COLUMN_NAME, IS_NULLABLE FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE()"
                " AND TABLE_NAME = 'equipment_documents' AND COLUMN_NAME IN ('action_id', 'procedure_id', 'kind')"
                " ORDER BY ORDINAL_POSITION") == [
        {"COLUMN_NAME": "action_id", "IS_NULLABLE": "YES"}, {"COLUMN_NAME": "procedure_id", "IS_NULLABLE": "YES"},
        {"COLUMN_NAME": "kind", "IS_NULLABLE": "NO"}]
    assert {"INDEX_NAME": "ix_equipment_documents_procedure", "NON_UNIQUE": 1, "cols": "procedure_id,removed_at"} in (
        _keys("equipment_documents"))
    assert {"CONSTRAINT_NAME": "fk_equipment_documents_procedure", "REFERENCED_TABLE_NAME": "procedures"} in (
        _foreign_keys("equipment_documents"))
    assert "procedure_id" in _owner_check_clause()[0]["CHECK_CLAUSE"]


def test_a_v40_database_keeps_every_row():
    _a_v40_database_with_rows()
    documents_before = _run("SELECT * FROM equipment_documents ORDER BY id")
    _migrate(V41)
    assert _versions() == VERSIONS
    documents_after = _run("SELECT * FROM equipment_documents ORDER BY id")
    assert [{k: v for k, v in row.items() if k != "procedure_id"} for row in documents_after] == documents_before
    assert [row["procedure_id"] for row in documents_after] == [None, None, None, None]


def test_a_document_has_exactly_one_of_five_owners():
    action_id = _a_v40_database_with_rows()
    _migrate(V41)
    lesson_id = _add_lesson("OPL-001")
    _add_document("procedure_id", lesson_id, "lesson.jpg")
    with pytest.raises(pymysql.err.OperationalError) as refused:
        _run("INSERT INTO equipment_documents (action_id, procedure_id, kind, title, original_name, stored_name,"
             " content_type, size_bytes, created_by) VALUES (%s, %s, 'photo', 'x', 'x.jpg', 'two.jpg', 'image/jpeg',"
             " 1, 'kla')", (action_id, lesson_id))
    assert refused.value.args[0] == ER_CONSTRAINT_FAILED
    assert "chk_equipment_documents_owner" in refused.value.args[1]


def test_one_lesson_per_countermeasure_and_any_number_without_one():
    action_id = _a_v40_database_with_rows()
    _migrate(V41)
    _add_lesson("OPL-001", action_id)
    with pytest.raises(pymysql.err.IntegrityError) as refused:
        _add_lesson("OPL-002", action_id)
    assert refused.value.args[0] == ER_DUP_ENTRY and "uq_procedures_action" in refused.value.args[1]
    _add_lesson("OPL-003")
    _add_lesson("OPL-004")
    assert _run("SELECT COUNT(*) AS n FROM procedures WHERE action_id IS NULL") == [{"n": 2}]


def test_tamil_text_at_the_bounds_is_stored_whole():
    """VARCHAR counts characters (code points), as Python's len: a Tamil letter with a vowel sign is two."""
    _a_v40_database_with_rows()
    _migrate(V41)
    title, body = "கொ" * 40, "வரி" * 333 + "க"
    assert (len(title), len(body)) == (80, 1000)
    lesson_id = _add_lesson("OPL-001", title=title, body=body)
    assert _run("SELECT title, body FROM procedures WHERE id = %s", (lesson_id,)) == [{"title": title, "body": body}]


def test_a_rerun_changes_nothing():
    _a_v40_database_with_rows()
    _migrate(V41)
    lesson_id = _add_lesson("OPL-001")
    _add_document("procedure_id", lesson_id, "lesson.jpg")
    schema = _schema()
    kept = (_run("SELECT * FROM procedures"), _run("SELECT * FROM equipment_documents ORDER BY id"))
    _run("DELETE FROM db_version WHERE version = 41")
    _migrate(V41)
    assert _schema() == schema
    assert (_run("SELECT * FROM procedures"), _run("SELECT * FROM equipment_documents ORDER BY id")) == kept
    assert _versions() == VERSIONS


def test_a_half_applied_v41_adds_the_owner_check_again():
    _a_v40_database_with_rows()
    _migrate(V41)
    schema = _schema()
    _run("ALTER TABLE equipment_documents DROP CONSTRAINT chk_equipment_documents_owner")
    _run("DELETE FROM db_version WHERE version = 41")
    assert not _owner_check_clause()
    _migrate(V41)
    assert _schema() == schema
    assert "procedure_id" in _owner_check_clause()[0]["CHECK_CLAUSE"]
    assert _versions() == VERSIONS
