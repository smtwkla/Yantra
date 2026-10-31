"""v47, one renewal per contract (S085 § 4.1, § 8.1), in the upgrade database UPGRADE_DB that the v20-v46 migration
tests also use (one per test run and worker, tests/db_names.py).  A fresh database gets the unique key
uq_contracts_renewal_of in place of the plain ix_contracts_renewal_of, and keeps fk_contracts_renewal_of; a v46
database with a contract and its renewal keeps both; a second renewal of one contract is refused; many contracts
renew nothing; a re-run changes nothing.  Needs the dev MariaDB container.
"""

import pymysql
import pytest

import local_db
from tests.test_migration_v20 import _migrate, _run, _schema
from tests.test_migration_v36 import _foreign_keys, _keys
from tests.test_migration_v43 import _a_v42_database_with_a_site_and_a_vendor, _add_contract

V46 = [m for m in local_db._MIGRATIONS if m[0] in range(20, 47)]
V47 = [m for m in local_db._MIGRATIONS if m[0] in range(20, 48)]
VERSIONS = list(range(20, 48))

ER_DUP_ENTRY = 1062


def _versions():
    return [r["version"] for r in _run("SELECT version FROM db_version ORDER BY version")]


def _a_v46_database_with_a_renewal():
    """A v46 database with a site, a vendor, a contract and its renewal -> (site_id, vendor_id, old contract id)."""
    site_id, vendor_id = _a_v42_database_with_a_site_and_a_vendor()
    _migrate(V46)
    _add_contract(site_id, vendor_id)
    old_id = _run("SELECT id FROM contracts")[0]["id"]
    _add_contract(site_id, vendor_id, title="Atlas Copco AMC 2027-28", from_date="2027-04-01",
                  to_date="2028-03-31", renewal_of_id=old_id)
    return site_id, vendor_id, old_id


def test_a_fresh_database_gets_v47():
    _a_v42_database_with_a_site_and_a_vendor()
    _migrate(V47)
    assert _versions() == VERSIONS
    assert _keys("contracts") == [
        {"INDEX_NAME": "ix_contracts_site", "NON_UNIQUE": 1, "cols": "site_id,active,to_date"},
        {"INDEX_NAME": "ix_contracts_vendor", "NON_UNIQUE": 1, "cols": "vendor_id"},
        {"INDEX_NAME": "PRIMARY", "NON_UNIQUE": 0, "cols": "id"},
        {"INDEX_NAME": "uq_contracts_renewal_of", "NON_UNIQUE": 0, "cols": "renewal_of_id"},
    ]
    assert _foreign_keys("contracts") == [
        {"CONSTRAINT_NAME": "fk_contracts_renewal_of", "REFERENCED_TABLE_NAME": "contracts"},
        {"CONSTRAINT_NAME": "fk_contracts_site", "REFERENCED_TABLE_NAME": "sites"},
        {"CONSTRAINT_NAME": "fk_contracts_vendor", "REFERENCED_TABLE_NAME": "vendors"},
    ]


def test_a_v46_database_keeps_its_contracts():
    _a_v46_database_with_a_renewal()
    kept = _run("SELECT * FROM contracts ORDER BY id")
    _migrate(V47)
    assert _run("SELECT * FROM contracts ORDER BY id") == kept
    assert _versions() == VERSIONS


def test_a_second_renewal_of_one_contract_is_refused():
    site_id, vendor_id, old_id = _a_v46_database_with_a_renewal()
    _migrate(V47)
    with pytest.raises(pymysql.err.IntegrityError) as refused:
        _add_contract(site_id, vendor_id, title="Second renewal", renewal_of_id=old_id)
    assert refused.value.args[0] == ER_DUP_ENTRY and "uq_contracts_renewal_of" in refused.value.args[1]


def test_many_contracts_renew_nothing():
    site_id, vendor_id = _a_v42_database_with_a_site_and_a_vendor()
    _migrate(V47)
    for n in range(3):
        _add_contract(site_id, vendor_id, title=f"Contract {n}")
    assert _run("SELECT COUNT(*) AS n FROM contracts WHERE renewal_of_id IS NULL") == [{"n": 3}]


def test_a_rerun_changes_nothing():
    _a_v46_database_with_a_renewal()
    _migrate(V47)
    schema = _schema()
    kept = _run("SELECT * FROM contracts ORDER BY id")
    _run("DELETE FROM db_version WHERE version = 47")
    _migrate(V47)
    assert _schema() == schema
    assert _run("SELECT * FROM contracts ORDER BY id") == kept
    assert _versions() == VERSIONS
