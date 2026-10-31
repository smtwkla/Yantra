"""v45, a contract's documents and photos (S083 § 4.1, § 8.1), in the upgrade database UPGRADE_DB that the v20-v44
migration tests also use (one per test run and worker, tests/db_names.py).  A fresh database gets
equipment_documents.contract_id with its key, its foreign key to contracts and the owner CHECK widened to six
owners; a v44 database with documents of all five owners keeps every row; the CHECK keeps a document to one owner;
a re-run changes nothing, and a half-applied v45 (the owner CHECK dropped, not added) adds it again.  Needs the dev
MariaDB container.
"""

import pymysql
import pytest

import local_db
from tests.test_migration_v20 import _migrate, _recreate, _run, _schema
from tests.test_migration_v22 import _fill_one_ticket
from tests.test_migration_v36 import _foreign_keys, _keys, _one_improvement
from tests.test_migration_v38 import _add_action, _add_document, _documents_of_three_owners, _owner_check_clause
from tests.test_migration_v41 import _add_lesson

V44 = [m for m in local_db._MIGRATIONS if m[0] in range(20, 45)]
V45 = [m for m in local_db._MIGRATIONS if m[0] in range(20, 46)]
VERSIONS = list(range(20, 46))

ER_CONSTRAINT_FAILED = 4025


def _versions():
    return [r["version"] for r in _run("SELECT version FROM db_version ORDER BY version")]


def _a_v44_database_with_rows():
    """v44 with a ticket, a countermeasure, a lesson, documents of all five owners and a contract at the one site
    -> (the lesson's id, the contract's id)."""
    _recreate()
    _migrate(V44)
    _fill_one_ticket()
    action_id = _add_action(_one_improvement())
    _documents_of_three_owners()
    _add_document("action_id", action_id, "action.jpg")
    lesson_id = _add_lesson("OPL-001")
    _add_document("procedure_id", lesson_id, "lesson.jpg")
    _run("INSERT INTO vendors (name, created_by) VALUES ('Fuji Electric', 'kla')")
    _run("INSERT INTO contracts (site_id, vendor_id, contract_type, title, from_date, to_date, created_by)"
         " SELECT s.id, v.id, 'amc', 'Fuji AMC 2026-27', '2026-04-01', '2027-03-31', 'kla' FROM sites s, vendors v")
    return lesson_id, _run("SELECT id FROM contracts")[0]["id"]


def test_a_fresh_database_gets_v45():
    _recreate()
    _migrate(V45)
    assert _versions() == VERSIONS
    assert _run("SELECT COLUMN_NAME, IS_NULLABLE FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE()"
                " AND TABLE_NAME = 'equipment_documents' AND COLUMN_NAME IN ('procedure_id', 'contract_id', 'kind')"
                " ORDER BY ORDINAL_POSITION") == [
        {"COLUMN_NAME": "procedure_id", "IS_NULLABLE": "YES"}, {"COLUMN_NAME": "contract_id", "IS_NULLABLE": "YES"},
        {"COLUMN_NAME": "kind", "IS_NULLABLE": "NO"}]
    assert {"INDEX_NAME": "ix_equipment_documents_contract", "NON_UNIQUE": 1, "cols": "contract_id,removed_at"} in (
        _keys("equipment_documents"))
    assert {"CONSTRAINT_NAME": "fk_equipment_documents_contract", "REFERENCED_TABLE_NAME": "contracts"} in (
        _foreign_keys("equipment_documents"))
    assert "contract_id" in _owner_check_clause()[0]["CHECK_CLAUSE"]


def test_a_v44_database_keeps_every_row():
    _a_v44_database_with_rows()
    documents_before = _run("SELECT * FROM equipment_documents ORDER BY id")
    _migrate(V45)
    assert _versions() == VERSIONS
    documents_after = _run("SELECT * FROM equipment_documents ORDER BY id")
    assert [{k: v for k, v in row.items() if k != "contract_id"} for row in documents_after] == documents_before
    assert [row["contract_id"] for row in documents_after] == [None] * 5


def test_a_document_has_exactly_one_of_six_owners():
    lesson_id, contract_id = _a_v44_database_with_rows()
    _migrate(V45)
    _add_document("contract_id", contract_id, "contract.pdf")
    assert _run("SELECT COUNT(*) AS n FROM equipment_documents WHERE contract_id = %s", (contract_id,)) == [{"n": 1}]
    with pytest.raises(pymysql.err.OperationalError) as refused:
        _run("INSERT INTO equipment_documents (procedure_id, contract_id, kind, title, original_name, stored_name,"
             " content_type, size_bytes, created_by) VALUES (%s, %s, 'photo', 'x', 'x.jpg', 'two.jpg', 'image/jpeg',"
             " 1, 'kla')", (lesson_id, contract_id))
    assert refused.value.args[0] == ER_CONSTRAINT_FAILED
    assert "chk_equipment_documents_owner" in refused.value.args[1]


def test_a_rerun_changes_nothing():
    _lesson_id, contract_id = _a_v44_database_with_rows()
    _migrate(V45)
    _add_document("contract_id", contract_id, "contract.pdf")
    schema = _schema()
    kept = _run("SELECT * FROM equipment_documents ORDER BY id")
    _run("DELETE FROM db_version WHERE version = 45")
    _migrate(V45)
    assert _schema() == schema
    assert _run("SELECT * FROM equipment_documents ORDER BY id") == kept
    assert _versions() == VERSIONS


def test_a_half_applied_v45_adds_the_owner_check_again():
    _a_v44_database_with_rows()
    _migrate(V45)
    schema = _schema()
    _run("ALTER TABLE equipment_documents DROP CONSTRAINT chk_equipment_documents_owner")
    _run("DELETE FROM db_version WHERE version = 45")
    assert not _owner_check_clause()
    _migrate(V45)
    assert _schema() == schema
    assert "contract_id" in _owner_check_clause()[0]["CHECK_CLAUSE"]
    assert _versions() == VERSIONS
