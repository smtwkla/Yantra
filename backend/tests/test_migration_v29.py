"""v29, meter types (S037 § 4), in the upgrade database UPGRADE_DB that the v20-v28 migration tests
also use (one per test run and worker, tests/db_names.py).  A v28 database gets the table and the
eight seed rows; the CHECK refuses a row of the wrong shape, one test per branch; a re-run adds
nothing.  Needs the dev MariaDB container.
"""

import pymysql
import pytest

import local_db
from tests.test_migration_v20 import _migrate, _recreate, _run, _schema

V28 = [m for m in local_db._MIGRATIONS if m[0] in range(20, 29)]
V29 = [m for m in local_db._MIGRATIONS if m[0] in range(20, 30)]
VERSIONS = list(range(20, 30))

SEED = [
    ("Energy", "kWh", "counter", None, 1), ("Fuel level", "%", "gauge", None, 0),
    ("Odometer", "km", "counter", None, 0), ("Oil temperature", "°C", "gauge", None, 1),
    ("Production count", "pcs", "counter", None, 0), ("Run hours", "h", "counter", None, 1),
    ("Shift production", "pcs", "amount", None, 0), ("Strokes", "strokes", "counter", None, 0),
]


def _versions():
    return [r["version"] for r in _run("SELECT version FROM db_version ORDER BY version")]


def _table_exists():
    return bool(_run("SELECT 1 FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE()"
                     " AND TABLE_NAME = 'meter_types'"))


def _insert(name, unit, kind, answer, decimals):
    _run("INSERT INTO meter_types (name, unit, kind, expected_answer, decimals, created_by)"
         " VALUES (%s, %s, %s, %s, %s, 'kla')", (name, unit, kind, answer, decimals))


def test_a_v28_database_gets_v29_with_the_eight_seed_rows():
    _recreate()
    _migrate(V28)
    assert not _table_exists()

    _migrate(V29)
    assert _versions() == VERSIONS
    rows = _run("SELECT name, unit, kind, expected_answer, decimals, active, created_by FROM meter_types"
                " ORDER BY name")
    assert [(r["name"], r["unit"], r["kind"], r["expected_answer"], r["decimals"]) for r in rows] == SEED
    assert {(r["active"], r["created_by"]) for r in rows} == {(1, "migration-v29")}


def test_the_name_is_unique_whatever_its_case():
    _recreate()
    _migrate(V29)
    with pytest.raises(pymysql.err.IntegrityError) as exc:
        _insert("RUN HOURS", "h", "counter", None, 0)
    assert "uq_meter_types_name" in str(exc.value)


@pytest.mark.parametrize("row, why", [
    (("Q1", "h", "yes_no", "yes", 0), "a yes_no row with a unit"),
    (("Q2", None, "yes_no", "yes", 1), "a yes_no row with decimals 1"),
    (("Q3", None, "yes_no", None, 0), "a yes_no row without an expected answer"),
    (("Q4", None, "counter", None, 0), "a counter row without a unit"),
    (("Q5", "h", "counter", "yes", 0), "a counter row with an expected answer"),
])
def test_the_yes_no_check_refuses_a_row_of_the_wrong_shape(row, why):
    _recreate()
    _migrate(V29)
    with pytest.raises(pymysql.err.OperationalError) as exc:
        _insert(*row)
    assert exc.value.args[0] == 4025 and "chk_meter_types_yes_no" in str(exc.value), why


def test_the_check_accepts_a_well_formed_yes_no_row_and_refuses_decimals_over_3():
    _recreate()
    _migrate(V29)
    _insert("Oil level above min", None, "yes_no", "yes", 0)
    with pytest.raises(pymysql.err.OperationalError) as exc:
        _insert("Pressure", "bar", "gauge", None, 4)
    assert exc.value.args[0] == 4025 and "chk_meter_types_decimals" in str(exc.value)


def test_running_v29_again_adds_nothing_and_keeps_an_edit():
    _recreate()
    _migrate(V29)
    _run("UPDATE meter_types SET unit = 'hrs' WHERE name = 'Run hours'")
    schema, count = _schema(), _run("SELECT COUNT(*) AS n FROM meter_types")
    _run("DELETE FROM db_version WHERE version = 29")
    _migrate(V29)
    assert _versions() == VERSIONS
    assert _schema() == schema
    assert _run("SELECT COUNT(*) AS n FROM meter_types") == count
    assert _run("SELECT unit FROM meter_types WHERE name = 'Run hours'") == [{"unit": "hrs"}]
