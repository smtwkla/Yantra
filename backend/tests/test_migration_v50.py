"""v50, v42–v47 squashed with S087's change: vendors and contracts, company-wide (S087 § 4.1, § 8.1), in the upgrade
database UPGRADE_DB (one per test run and worker, tests/db_names.py), dropped and created by these tests.

- the three shapes of § 4.2: (a) a fresh database after v41, (b) production at v41 with rows, (c) a dev or test
  database at v47 (and one stopped at v43), built from the frozen texts tests/fixtures/migrations_v47.py; (b) and (c)
  end with the fresh build's schema, every row kept, contracts without site_id;
- re-runs: a complete v50 run again changes nothing, and a half-applied one (the owner CHECK dropped) completes;
- the constraints moved from the removed test_migration_v42.py … v47.py, on the fresh build.

The v47 shape is built on the squashed v41 (SQUASHED) and then the fixture, never the fixture on an empty database.
Needs the dev MariaDB container.
"""

import pymysql
import pytest

import local_db
from tests.fixtures.migrations_v47 import MIGRATIONS_V42_V47
from tests.migration_helpers import SQUASHED, _migrate, _recreate, _run, _schema, _versions
from tests.test_migration_v22 import _fill_one_ticket
from tests.test_migration_v36 import _foreign_keys, _keys
from tests.test_migration_v38 import _add_document, _documents_of_three_owners, _owner_check_clause
from tests.test_migration_v41 import _add_lesson

V50 = local_db._MIGRATIONS
V43 = [*SQUASHED, *[m for m in MIGRATIONS_V42_V47 if m[0] <= 43]]
V47 = [*SQUASHED, *MIGRATIONS_V42_V47]

ER_CONSTRAINT_FAILED = 4025
ER_DUP_ENTRY = 1062
ER_NO_REFERENCED_ROW = 1452

CONTRACT_COLUMNS = [
    "id", "vendor_id", "contract_type", "title", "contract_number", "from_date", "to_date", "first_reminder_for",
    "second_reminder_for", "covers_labour", "covers_parts", "covers_consumables", "covers_breakdown_calls",
    "breakdown_calls_per_year", "covered_text", "not_covered_text", "pm_visits_per_year", "response_hours",
    "only_vendor_repairs", "callout_number", "cost_note", "notes", "renewal_of_id", "active", "created_at",
    "created_by", "updated_at", "updated_by"]


@pytest.fixture(scope="module")
def fresh():
    """The schema v41 then v50 build on an empty database."""
    _recreate()
    _migrate(V50)
    return _schema()


def _columns(table):
    return [r["COLUMN_NAME"] for r in _run(
        "SELECT COLUMN_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s"
        " ORDER BY ORDINAL_POSITION", (table,))]


def _add_vendor(name="Atlas Copco"):
    _run("INSERT INTO vendors (name, created_by) VALUES (%s, 'kla')", (name,))
    return _run("SELECT id FROM vendors WHERE name = %s", (name,))[0]["id"]


def _add_person(name, employment, vendor_id=None):
    _run("INSERT INTO people (name, employment, vendor_id, created_by) VALUES (%s, %s, %s, 'kla')",
         (name, employment, vendor_id))
    return _run("SELECT id FROM people WHERE name = %s", (name,))[0]["id"]


def _add_contract(vendor_id, **fields):
    """A contract without a site (v50's shape) -> its id."""
    row = {"vendor_id": vendor_id, "contract_type": "amc", "title": "Atlas Copco AMC", "from_date": "2026-04-01",
           "to_date": "2027-03-31", "created_by": "kla", **fields}
    _run(f"INSERT INTO contracts ({', '.join(row)}) VALUES ({', '.join(['%s'] * len(row))})", list(row.values()))
    return _run("SELECT MAX(id) AS id FROM contracts")[0]["id"]


def _add_line(contract_id, equipment_id, price=None):
    _run("INSERT INTO contract_equipment (contract_id, equipment_id, price, created_by) VALUES (%s, %s, %s, 'kla')",
         (contract_id, equipment_id, price))


def _machine(code="HP001"):
    return _run("SELECT id FROM equipment WHERE code = %s", (code,))[0]["id"]


def _second_machine_at_a_second_site():
    """A site BRICKS with a unit and a machine HP002 -> the machine's id."""
    _run("INSERT INTO sites (code, name, created_by) VALUES ('BRICKS', 'Bricks plant', 'kla')")
    _run("INSERT INTO units (site_id, code, name, created_by) SELECT id, 'FILTER', 'Filter', 'kla' FROM sites"
         " WHERE code = 'BRICKS'")
    _run("INSERT INTO equipment (code, level, unit_id, class_id, model_id, name, created_by)"
         " SELECT 'HP002', 'equipment', u.id, e.class_id, e.model_id, 'Press 2', 'kla' FROM units u, equipment e"
         " WHERE u.code = 'FILTER' AND e.code = 'HP001'")
    return _machine("HP002")


def _fresh_with_a_machine():
    """The fresh build with a site, a unit, a machine and a vendor -> (vendor_id, equipment_id)."""
    _recreate()
    _migrate(V50)
    _fill_one_ticket()
    return _add_vendor(), _machine()


def _everything(tables):
    return {table: _run(f"SELECT * FROM {table} ORDER BY id") for table in tables}


def _without(rows, column):
    return [{k: v for k, v in row.items() if k != column} for row in rows]


# --- The three shapes -------------------------------------------------------------------------------------------


def test_a_fresh_database_gets_v50(fresh):
    assert _versions() == [41, 50]
    assert _columns("contracts") == CONTRACT_COLUMNS
    assert _keys("contracts") == [
        {"INDEX_NAME": "ix_contracts_active_to", "NON_UNIQUE": 1, "cols": "active,to_date"},
        {"INDEX_NAME": "ix_contracts_vendor", "NON_UNIQUE": 1, "cols": "vendor_id"},
        {"INDEX_NAME": "PRIMARY", "NON_UNIQUE": 0, "cols": "id"},
        {"INDEX_NAME": "uq_contracts_renewal_of", "NON_UNIQUE": 0, "cols": "renewal_of_id"},
    ]
    assert _foreign_keys("contracts") == [
        {"CONSTRAINT_NAME": "fk_contracts_renewal_of", "REFERENCED_TABLE_NAME": "contracts"},
        {"CONSTRAINT_NAME": "fk_contracts_vendor", "REFERENCED_TABLE_NAME": "vendors"},
    ]
    assert _columns("vendors") == [
        "id", "name", "phone", "note", "active", "created_at", "created_by", "updated_at", "updated_by"]
    assert _keys("contract_equipment") == [
        {"INDEX_NAME": "ix_contract_equipment_equipment", "NON_UNIQUE": 1, "cols": "equipment_id"},
        {"INDEX_NAME": "PRIMARY", "NON_UNIQUE": 0, "cols": "id"},
        {"INDEX_NAME": "uq_contract_equipment", "NON_UNIQUE": 0, "cols": "contract_id,equipment_id"},
    ]
    people = _columns("people")
    assert people[people.index("employment") + 1] == "vendor_id"
    assert {"CONSTRAINT_NAME": "fk_people_vendor", "REFERENCED_TABLE_NAME": "vendors"} in _foreign_keys("people")
    documents = _columns("equipment_documents")
    assert documents[documents.index("procedure_id") + 1] == "contract_id"
    assert {"CONSTRAINT_NAME": "fk_equipment_documents_contract", "REFERENCED_TABLE_NAME": "contracts"} in (
        _foreign_keys("equipment_documents"))
    assert "contract_id" in _owner_check_clause()[0]["CHECK_CLAUSE"]
    event = _run("SELECT COLUMN_TYPE FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE()"
                 " AND TABLE_NAME = 'equipment_events' AND COLUMN_NAME = 'event'")[0]["COLUMN_TYPE"]
    assert event.endswith(",'property','contract_added','contract_removed')")


def test_production_at_v41_gets_the_fresh_schema(fresh):
    _recreate()
    _migrate(SQUASHED)
    _fill_one_ticket()
    _run("INSERT INTO people (name, employment, username, created_by) VALUES ('Priya', 'direct', 'priya', 'kla')")
    _documents_of_three_owners()
    people, documents = _run("SELECT * FROM people ORDER BY id"), _run("SELECT * FROM equipment_documents ORDER BY id")
    sites = _run("SELECT * FROM sites ORDER BY id")

    _migrate(V50)
    assert _versions() == [41, 50]
    assert _schema() == fresh
    assert _run("SELECT * FROM sites ORDER BY id") == sites
    after = _run("SELECT * FROM people ORDER BY id")
    assert _without(after, "vendor_id") == people and {r["vendor_id"] for r in after} == {None}
    after = _run("SELECT * FROM equipment_documents ORDER BY id")
    assert _without(after, "contract_id") == documents and {r["contract_id"] for r in after} == {None}


def _a_v47_database_with_rows():
    """v47 with two sites, a vendor linked to a contractor, a contract at each site with a line, a renewal, a
    reminder marker and a contract document."""
    _recreate()
    _migrate(V47)
    _fill_one_ticket()
    bricks_machine = _second_machine_at_a_second_site()
    vendor_id = _add_vendor()
    _add_person("Atlas Copco service", "contractor", vendor_id)
    for code, title, marker in (("SMTW", "Atlas Copco AMC", "2027-03-31"), ("BRICKS", "Atlas Copco AMC B", None)):
        _run("INSERT INTO contracts (site_id, vendor_id, contract_type, title, from_date, to_date, first_reminder_for,"
             " created_by) SELECT id, %s, 'amc', %s, '2026-04-01', '2027-03-31', %s, 'kla' FROM sites WHERE code = %s",
             (vendor_id, title, marker, code))
    smtw_id, bricks_id = [r["id"] for r in _run("SELECT id FROM contracts ORDER BY id")]
    _add_line(smtw_id, _machine(), "9809")
    _add_line(bricks_id, bricks_machine)
    _run("INSERT INTO contracts (site_id, vendor_id, contract_type, title, from_date, to_date, renewal_of_id,"
         " created_by) SELECT site_id, vendor_id, 'amc', 'Atlas Copco AMC 2027-28', '2027-04-01', '2028-03-31', id,"
         " 'kla' FROM contracts WHERE id = %s", (smtw_id,))
    _add_document("contract_id", smtw_id, "contract.pdf")


TABLES = ("sites", "units", "equipment", "vendors", "people", "contract_equipment", "equipment_documents")


def test_dev_at_v47_converges(fresh):
    _a_v47_database_with_rows()
    kept = _everything(TABLES)
    contracts = _run("SELECT * FROM contracts ORDER BY id")
    assert {r["site_id"] for r in contracts} != {None}

    _migrate(V50)
    assert _versions() == [41, 42, 43, 44, 45, 46, 47, 50]
    assert _schema() == fresh
    assert _everything(TABLES) == kept
    assert _run("SELECT * FROM contracts ORDER BY id") == _without(contracts, "site_id")


def test_dev_at_v43_converges(fresh):
    _recreate()
    _migrate(V43)
    _fill_one_ticket()
    vendor_id = _add_vendor()
    _run("INSERT INTO contracts (site_id, vendor_id, contract_type, title, from_date, to_date, created_by)"
         " SELECT id, %s, 'amc', 'Atlas Copco AMC', '2026-04-01', '2027-03-31', 'kla' FROM sites", (vendor_id,))
    contracts = _run("SELECT * FROM contracts ORDER BY id")

    _migrate(V50)
    assert _versions() == [41, 42, 43, 50]
    assert _schema() == fresh
    after = _run("SELECT * FROM contracts ORDER BY id")
    assert [{k: v for k, v in r.items() if k not in ("first_reminder_for", "second_reminder_for")} for r in after] == (
        _without(contracts, "site_id"))
    assert [(r["first_reminder_for"], r["second_reminder_for"]) for r in after] == [(None, None)]


@pytest.mark.parametrize("shape", ["fresh", "production", "dev"])
def test_a_rerun_changes_nothing(fresh, shape):
    if shape == "dev":
        _a_v47_database_with_rows()
    else:
        _recreate()
        _migrate(SQUASHED)
        if shape == "production":
            _fill_one_ticket()
    _migrate(V50)
    schema = _schema()
    kept = _everything((*TABLES, "contracts"))
    _run("DELETE FROM db_version WHERE version = 50")
    _migrate(V50)
    assert _schema() == schema == fresh
    assert _everything((*TABLES, "contracts")) == kept
    assert 50 in _versions()


def test_a_half_applied_v50_converges(fresh):
    """The window between step 8's drop and add of the owner CHECK; a stop inside step 5 re-runs the same way."""
    _recreate()
    _migrate(V50)
    _run("ALTER TABLE equipment_documents DROP CONSTRAINT chk_equipment_documents_owner")
    _run("DELETE FROM db_version WHERE version = 50")
    assert not _owner_check_clause()
    _migrate(V50)
    assert _schema() == fresh
    assert "contract_id" in _owner_check_clause()[0]["CHECK_CLAUSE"]
    assert _versions() == [41, 50]


# --- Constraints, moved from test_migration_v42.py … v47.py (S088 D6) ----------------------------------------------


def test_the_check_keeps_a_vendor_to_a_contractor():
    vendor_id, _equipment_id = _fresh_with_a_machine()
    with pytest.raises(pymysql.err.OperationalError) as refused:
        _add_person("Priya", "direct", vendor_id)
    assert refused.value.args[0] == ER_CONSTRAINT_FAILED and "chk_people_vendor" in refused.value.args[1]
    person_id = _add_person("Atlas Copco service", "contractor", vendor_id)
    with pytest.raises(pymysql.err.OperationalError) as refused:
        _run("UPDATE people SET employment = 'direct' WHERE id = %s", (person_id,))
    assert refused.value.args[0] == ER_CONSTRAINT_FAILED and "chk_people_vendor" in refused.value.args[1]


def test_an_unknown_vendor_is_refused():
    _fresh_with_a_machine()
    with pytest.raises(pymysql.err.IntegrityError) as refused:
        _add_person("Atlas Copco service", "contractor", 999)
    assert refused.value.args[0] == ER_NO_REFERENCED_ROW and "fk_people_vendor" in refused.value.args[1]
    with pytest.raises(pymysql.err.IntegrityError) as refused:
        _add_contract(999)
    assert refused.value.args[0] == ER_NO_REFERENCED_ROW and "fk_contracts_vendor" in refused.value.args[1]


def test_the_name_is_unique_in_any_case():
    _fresh_with_a_machine()
    with pytest.raises(pymysql.err.IntegrityError) as refused:
        _add_vendor("atlas copco")
    assert refused.value.args[0] == ER_DUP_ENTRY and "uq_vendors_name" in refused.value.args[1]


def _refused_by(check, vendor_id, **fields):
    with pytest.raises(pymysql.err.OperationalError) as refused:
        _add_contract(vendor_id, **fields)
    assert refused.value.args[0] == ER_CONSTRAINT_FAILED and check in refused.value.args[1]


def test_the_contract_checks_and_their_boundaries():
    vendor_id, _equipment_id = _fresh_with_a_machine()
    _refused_by("chk_contracts_period", vendor_id, from_date="2027-04-01", to_date="2027-03-31")
    _refused_by("chk_contracts_pm_visits", vendor_id, pm_visits_per_year=53)
    _refused_by("chk_contracts_response", vendor_id, response_hours=0)
    _refused_by("chk_contracts_response", vendor_id, response_hours=721)
    _refused_by("chk_contracts_breakdown_calls", vendor_id, covers_breakdown_calls=0, breakdown_calls_per_year=4)
    _refused_by("chk_contracts_breakdown_calls", vendor_id, covers_breakdown_calls=1, breakdown_calls_per_year=366)
    assert _run("SELECT COUNT(*) AS n FROM contracts") == [{"n": 0}]
    _add_contract(vendor_id, from_date="2027-03-31", to_date="2027-03-31")
    for visits in (0, 52):
        _add_contract(vendor_id, pm_visits_per_year=visits)
    for hours in (1, 720):
        _add_contract(vendor_id, response_hours=hours)
    for calls in (1, 365):
        _add_contract(vendor_id, covers_breakdown_calls=1, breakdown_calls_per_year=calls)
    assert _run("SELECT COUNT(*) AS n FROM contracts") == [{"n": 7}]


def test_one_vendor_contract_number_may_repeat():
    """S080 D7: a mixed quote is entered as two contracts with the same vendor and number."""
    vendor_id, _equipment_id = _fresh_with_a_machine()
    _add_contract(vendor_id, contract_number="AMC-0000-R", contract_type="amc")
    _add_contract(vendor_id, contract_number="AMC-0000-R", contract_type="cmc")
    assert _run("SELECT COUNT(*) AS n FROM contracts WHERE contract_number = 'AMC-0000-R'") == [{"n": 2}]


def test_the_price_check():
    vendor_id, equipment_id = _fresh_with_a_machine()
    contract_id = _add_contract(vendor_id)
    with pytest.raises(pymysql.err.OperationalError) as refused:
        _add_line(contract_id, equipment_id, "-0.01")
    assert refused.value.args[0] == ER_CONSTRAINT_FAILED and "chk_contract_equipment_price" in refused.value.args[1]
    _add_line(contract_id, equipment_id, "0")
    _add_line(contract_id, _second_machine_at_a_second_site(), "99999999.99")
    assert [str(r["price"]) for r in _run("SELECT price FROM contract_equipment ORDER BY id")] == [
        "0.00", "99999999.99"]


def test_a_node_twice_and_unknown_rows_are_refused():
    vendor_id, equipment_id = _fresh_with_a_machine()
    contract_id = _add_contract(vendor_id)
    _add_line(contract_id, equipment_id)
    with pytest.raises(pymysql.err.IntegrityError) as refused:
        _add_line(contract_id, equipment_id, "10")
    assert refused.value.args[0] == ER_DUP_ENTRY and "uq_contract_equipment" in refused.value.args[1]
    for bad_contract, bad_node, key in ((999999, equipment_id, "fk_contract_equipment_contract"),
                                        (contract_id, 999999, "fk_contract_equipment_equipment")):
        with pytest.raises(pymysql.err.IntegrityError) as refused:
            _add_line(bad_contract, bad_node)
        assert refused.value.args[0] == ER_NO_REFERENCED_ROW and key in refused.value.args[1]


def test_the_new_history_kinds_are_stored():
    _vendor_id, equipment_id = _fresh_with_a_machine()
    for kind in ("contract_added", "contract_removed"):
        _run("INSERT INTO equipment_events (equipment_id, event, old_value, new_value, created_by)"
             " VALUES (%s, %s, NULL, 'x', 'kla')", (equipment_id, kind))
    assert _run("SELECT COUNT(*) AS n FROM equipment_events WHERE event IN ('contract_added', 'contract_removed')"
                ) == [{"n": 2}]


def test_a_document_has_exactly_one_of_six_owners():
    vendor_id, _equipment_id = _fresh_with_a_machine()
    contract_id = _add_contract(vendor_id)
    lesson_id = _add_lesson("OPL-001")
    _add_document("contract_id", contract_id, "contract.pdf")
    assert _run("SELECT COUNT(*) AS n FROM equipment_documents WHERE contract_id = %s", (contract_id,)) == [{"n": 1}]
    with pytest.raises(pymysql.err.OperationalError) as refused:
        _run("INSERT INTO equipment_documents (procedure_id, contract_id, kind, title, original_name, stored_name,"
             " content_type, size_bytes, created_by) VALUES (%s, %s, 'photo', 'x', 'x.jpg', 'two.jpg', 'image/jpeg',"
             " 1, 'kla')", (lesson_id, contract_id))
    assert refused.value.args[0] == ER_CONSTRAINT_FAILED
    assert "chk_equipment_documents_owner" in refused.value.args[1]


def test_a_second_renewal_of_one_contract_is_refused():
    vendor_id, _equipment_id = _fresh_with_a_machine()
    old_id = _add_contract(vendor_id)
    _add_contract(vendor_id, title="Atlas Copco AMC 2027-28", from_date="2027-04-01", to_date="2028-03-31",
                  renewal_of_id=old_id)
    with pytest.raises(pymysql.err.IntegrityError) as refused:
        _add_contract(vendor_id, title="Second renewal", renewal_of_id=old_id)
    assert refused.value.args[0] == ER_DUP_ENTRY and "uq_contracts_renewal_of" in refused.value.args[1]


def test_many_contracts_renew_nothing():
    vendor_id, _equipment_id = _fresh_with_a_machine()
    for n in range(3):
        _add_contract(vendor_id, title=f"Contract {n}")
    assert _run("SELECT COUNT(*) AS n FROM contracts WHERE renewal_of_id IS NULL") == [{"n": 3}]
