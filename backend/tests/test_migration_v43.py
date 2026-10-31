"""v43, vendor contracts (S080 § 4.1, § 8.1), in the upgrade database UPGRADE_DB that the v20-v42 migration tests
also use (one per test run and worker, tests/db_names.py).  A fresh database gets the table contracts with its keys,
foreign keys and CHECKs; a v42 database with a site and a vendor keeps both; the CHECKs refuse a period ending
before it starts, out-of-range visits, hours and calls, and calls per year without the tick, and pass the
boundaries; an unknown vendor is refused; one vendor's contract number may repeat (D7); a re-run changes nothing.
Needs the dev MariaDB container.
"""

import pymysql
import pytest

import local_db
from tests.migration_helpers import _migrate, _recreate, _run, _schema
from tests.test_migration_v36 import _foreign_keys, _keys

V42 = [m for m in local_db._MIGRATIONS if m[0] in range(20, 43)]
V43 = [m for m in local_db._MIGRATIONS if m[0] in range(20, 44)]
VERSIONS = [41, *range(42, 44)]

ER_CONSTRAINT_FAILED = 4025
ER_NO_REFERENCED_ROW = 1452


def _versions():
    return [r["version"] for r in _run("SELECT version FROM db_version ORDER BY version")]


def _a_v42_database_with_a_site_and_a_vendor():
    _recreate()
    _migrate(V42)
    _run("INSERT INTO sites (code, name, created_by) VALUES ('SMTW', 'SMTW plant', 'kla')")
    _run("INSERT INTO vendors (name, created_by) VALUES ('Atlas Copco', 'kla')")
    return (_run("SELECT id FROM sites WHERE code = 'SMTW'")[0]["id"],
            _run("SELECT id FROM vendors WHERE name = 'Atlas Copco'")[0]["id"])


def _fresh_v43():
    site_id, vendor_id = _a_v42_database_with_a_site_and_a_vendor()
    _migrate(V43)
    return site_id, vendor_id


def _add_contract(site_id, vendor_id, **fields):
    row = {"site_id": site_id, "vendor_id": vendor_id, "contract_type": "amc", "title": "Atlas Copco AMC",
           "from_date": "2026-04-01", "to_date": "2027-03-31", "created_by": "kla", **fields}
    _run(f"INSERT INTO contracts ({', '.join(row)}) VALUES ({', '.join(['%s'] * len(row))})", list(row.values()))


def _refused_by(check, site_id, vendor_id, **fields):
    with pytest.raises(pymysql.err.OperationalError) as refused:
        _add_contract(site_id, vendor_id, **fields)
    assert refused.value.args[0] == ER_CONSTRAINT_FAILED and check in refused.value.args[1]


def test_a_fresh_database_gets_v43():
    _recreate()
    _migrate(V43)
    assert _versions() == VERSIONS
    assert _run("SELECT COUNT(*) AS n FROM contracts") == [{"n": 0}]
    assert _keys("contracts") == [
        {"INDEX_NAME": "ix_contracts_renewal_of", "NON_UNIQUE": 1, "cols": "renewal_of_id"},
        {"INDEX_NAME": "ix_contracts_site", "NON_UNIQUE": 1, "cols": "site_id,active,to_date"},
        {"INDEX_NAME": "ix_contracts_vendor", "NON_UNIQUE": 1, "cols": "vendor_id"},
        {"INDEX_NAME": "PRIMARY", "NON_UNIQUE": 0, "cols": "id"},
    ]
    assert _foreign_keys("contracts") == [
        {"CONSTRAINT_NAME": "fk_contracts_renewal_of", "REFERENCED_TABLE_NAME": "contracts"},
        {"CONSTRAINT_NAME": "fk_contracts_site", "REFERENCED_TABLE_NAME": "sites"},
        {"CONSTRAINT_NAME": "fk_contracts_vendor", "REFERENCED_TABLE_NAME": "vendors"},
    ]


def test_a_v42_database_keeps_its_site_and_vendor():
    _a_v42_database_with_a_site_and_a_vendor()
    kept = (_run("SELECT * FROM sites ORDER BY id"), _run("SELECT * FROM vendors ORDER BY id"))
    _migrate(V43)
    assert _versions() == VERSIONS
    assert (_run("SELECT * FROM sites ORDER BY id"), _run("SELECT * FROM vendors ORDER BY id")) == kept


def test_the_checks_refuse_out_of_range_values():
    site_id, vendor_id = _fresh_v43()
    _refused_by("chk_contracts_period", site_id, vendor_id, from_date="2027-04-01", to_date="2027-03-31")
    _refused_by("chk_contracts_pm_visits", site_id, vendor_id, pm_visits_per_year=53)
    _refused_by("chk_contracts_response", site_id, vendor_id, response_hours=0)
    _refused_by("chk_contracts_response", site_id, vendor_id, response_hours=721)
    _refused_by("chk_contracts_breakdown_calls", site_id, vendor_id, covers_breakdown_calls=0,
                breakdown_calls_per_year=4)
    _refused_by("chk_contracts_breakdown_calls", site_id, vendor_id, covers_breakdown_calls=1,
                breakdown_calls_per_year=366)
    assert _run("SELECT COUNT(*) AS n FROM contracts") == [{"n": 0}]


def test_the_boundaries_pass():
    site_id, vendor_id = _fresh_v43()
    _add_contract(site_id, vendor_id, from_date="2027-03-31", to_date="2027-03-31")
    for visits in (0, 52):
        _add_contract(site_id, vendor_id, pm_visits_per_year=visits)
    for hours in (1, 720):
        _add_contract(site_id, vendor_id, response_hours=hours)
    for calls in (1, 365):
        _add_contract(site_id, vendor_id, covers_breakdown_calls=1, breakdown_calls_per_year=calls)
    assert _run("SELECT COUNT(*) AS n FROM contracts") == [{"n": 7}]


def test_an_unknown_vendor_is_refused():
    site_id, _vendor_id = _fresh_v43()
    with pytest.raises(pymysql.err.IntegrityError) as refused:
        _add_contract(site_id, 999)
    assert refused.value.args[0] == ER_NO_REFERENCED_ROW and "fk_contracts_vendor" in refused.value.args[1]


def test_one_vendor_contract_number_may_repeat():
    """D7: a mixed quote is entered as two contracts with the same vendor and number."""
    site_id, vendor_id = _fresh_v43()
    _add_contract(site_id, vendor_id, contract_number="AMC-0000-R", contract_type="amc")
    _add_contract(site_id, vendor_id, contract_number="AMC-0000-R", contract_type="cmc")
    assert _run("SELECT COUNT(*) AS n FROM contracts WHERE contract_number = 'AMC-0000-R'") == [{"n": 2}]


def test_a_rerun_changes_nothing():
    site_id, vendor_id = _fresh_v43()
    _add_contract(site_id, vendor_id)
    schema = _schema()
    kept = _run("SELECT * FROM contracts")
    _run("DELETE FROM db_version WHERE version = 43")
    _migrate(V43)
    assert _schema() == schema
    assert _run("SELECT * FROM contracts") == kept
    assert _versions() == VERSIONS
