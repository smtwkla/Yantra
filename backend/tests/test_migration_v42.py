"""v42, the vendor master and a contractor's vendor (S079 § 4.1, § 8.1), in the upgrade database UPGRADE_DB that
the v20-v41 migration tests also use (one per test run and worker, tests/db_names.py).  A fresh database gets the
table vendors with its unique name, and people.vendor_id with its key, foreign key and the CHECK that keeps a vendor
to a contractor; a v41 database with people keeps every row, vendor_id NULL; an unknown vendor and a second spelling
in another case are refused; a re-run changes nothing, and a half-applied v42 (the CHECK not added) adds it again.
Needs the dev MariaDB container.
"""

import pymysql
import pytest

import local_db
from tests.migration_helpers import _migrate, _recreate, _run, _schema
from tests.test_migration_v36 import _foreign_keys, _keys

V41 = [m for m in local_db._MIGRATIONS if m[0] in range(20, 42)]
V42 = [m for m in local_db._MIGRATIONS if m[0] in range(20, 43)]
VERSIONS = [41, *range(42, 43)]

ER_CONSTRAINT_FAILED = 4025
ER_DUP_ENTRY = 1062
ER_NO_REFERENCED_ROW = 1452


def _versions():
    return [r["version"] for r in _run("SELECT version FROM db_version ORDER BY version")]


def _vendor_check_clause():
    return _run("SELECT CHECK_CLAUSE FROM information_schema.CHECK_CONSTRAINTS WHERE CONSTRAINT_SCHEMA = DATABASE()"
                " AND TABLE_NAME = 'people' AND CONSTRAINT_NAME = 'chk_people_vendor'")


def _add_vendor(name="Atlas Copco"):
    _run("INSERT INTO vendors (name, created_by) VALUES (%s, 'kla')", (name,))
    return _run("SELECT id FROM vendors WHERE name = %s", (name,))[0]["id"]


def _add_person(name, employment, vendor_id=None):
    _run("INSERT INTO people (name, employment, vendor_id, created_by) VALUES (%s, %s, %s, 'kla')",
         (name, employment, vendor_id))
    return _run("SELECT id FROM people WHERE name = %s", (name,))[0]["id"]


def _a_v41_database_with_people():
    """v41 with a direct person with a login, a contractor and an inactive person."""
    _recreate()
    _migrate(V41)
    _run("INSERT INTO people (name, employment, username, created_by) VALUES ('Priya', 'direct', 'priya', 'kla')")
    _run("INSERT INTO people (name, employment, created_by) VALUES ('Atlas Copco service', 'contractor', 'kla')")
    _run("INSERT INTO people (name, employment, active, created_by) VALUES ('Old fitter', 'direct', 0, 'kla')")


def test_a_fresh_database_gets_v42():
    _recreate()
    _migrate(V42)
    assert _versions() == VERSIONS
    assert _run("SELECT COUNT(*) AS n FROM vendors") == [{"n": 0}]
    assert [r["COLUMN_NAME"] for r in _run(
        "SELECT COLUMN_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'vendors'"
        " ORDER BY ORDINAL_POSITION")] == [
        "id", "name", "phone", "note", "active", "created_at", "created_by", "updated_at", "updated_by"]
    assert _keys("vendors") == [
        {"INDEX_NAME": "PRIMARY", "NON_UNIQUE": 0, "cols": "id"},
        {"INDEX_NAME": "uq_vendors_name", "NON_UNIQUE": 0, "cols": "name"},
    ]
    assert _run("SELECT COLUMN_NAME, IS_NULLABLE FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE()"
                " AND TABLE_NAME = 'people' AND COLUMN_NAME IN ('employment', 'vendor_id')"
                " ORDER BY ORDINAL_POSITION") == [
        {"COLUMN_NAME": "employment", "IS_NULLABLE": "NO"}, {"COLUMN_NAME": "vendor_id", "IS_NULLABLE": "YES"}]
    assert {"INDEX_NAME": "ix_people_vendor", "NON_UNIQUE": 1, "cols": "vendor_id"} in _keys("people")
    assert {"CONSTRAINT_NAME": "fk_people_vendor", "REFERENCED_TABLE_NAME": "vendors"} in _foreign_keys("people")
    assert "vendor_id" in _vendor_check_clause()[0]["CHECK_CLAUSE"]


def test_a_v41_database_keeps_every_person():
    _a_v41_database_with_people()
    before = _run("SELECT * FROM people ORDER BY id")
    _migrate(V42)
    assert _versions() == VERSIONS
    after = _run("SELECT * FROM people ORDER BY id")
    assert [{k: v for k, v in row.items() if k != "vendor_id"} for row in after] == before
    assert [row["vendor_id"] for row in after] == [None, None, None]


def test_the_check_keeps_a_vendor_to_a_contractor():
    _recreate()
    _migrate(V42)
    vendor_id = _add_vendor()
    with pytest.raises(pymysql.err.OperationalError) as refused:
        _add_person("Priya", "direct", vendor_id)
    assert refused.value.args[0] == ER_CONSTRAINT_FAILED and "chk_people_vendor" in refused.value.args[1]
    person_id = _add_person("Atlas Copco service", "contractor", vendor_id)
    assert _run("SELECT vendor_id FROM people WHERE id = %s", (person_id,)) == [{"vendor_id": vendor_id}]
    with pytest.raises(pymysql.err.OperationalError) as refused:
        _run("UPDATE people SET employment = 'direct' WHERE id = %s", (person_id,))
    assert refused.value.args[0] == ER_CONSTRAINT_FAILED and "chk_people_vendor" in refused.value.args[1]


def test_an_unknown_vendor_is_refused():
    _recreate()
    _migrate(V42)
    with pytest.raises(pymysql.err.IntegrityError) as refused:
        _add_person("Atlas Copco service", "contractor", 999)
    assert refused.value.args[0] == ER_NO_REFERENCED_ROW and "fk_people_vendor" in refused.value.args[1]


def test_the_name_is_unique_in_any_case():
    _recreate()
    _migrate(V42)
    _add_vendor("Atlas Copco")
    with pytest.raises(pymysql.err.IntegrityError) as refused:
        _add_vendor("atlas copco")
    assert refused.value.args[0] == ER_DUP_ENTRY and "uq_vendors_name" in refused.value.args[1]


def test_a_rerun_changes_nothing():
    _a_v41_database_with_people()
    _migrate(V42)
    vendor_id = _add_vendor()
    _add_person("Linked", "contractor", vendor_id)
    schema = _schema()
    kept = (_run("SELECT * FROM vendors"), _run("SELECT * FROM people ORDER BY id"))
    _run("DELETE FROM db_version WHERE version = 42")
    _migrate(V42)
    assert _schema() == schema
    assert (_run("SELECT * FROM vendors"), _run("SELECT * FROM people ORDER BY id")) == kept
    assert _versions() == VERSIONS


def test_a_half_applied_v42_adds_the_check():
    _a_v41_database_with_people()
    _migrate(V42)
    schema = _schema()
    _run("ALTER TABLE people DROP CONSTRAINT chk_people_vendor")
    _run("DELETE FROM db_version WHERE version = 42")
    assert not _vendor_check_clause()
    _migrate(V42)
    assert _schema() == schema
    assert "vendor_id" in _vendor_check_clause()[0]["CHECK_CLAUSE"]
    assert _versions() == VERSIONS
