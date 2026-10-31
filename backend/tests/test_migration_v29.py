"""v29, meter types (S037 § 4) — now part of the squashed v41 (S088), in the upgrade database UPGRADE_DB
(one per test run and worker, tests/db_names.py).  The name is unique whatever its case; the CHECKs
refuse a row of the wrong shape, one test per branch.  The upgrade from v28, the fresh-shape check and
the re-run went with S088 (§ 8.2): the squash test (test_migration_squash_v41.py) compares the whole
schema and the seed rows with the old texts.  Needs the dev MariaDB container.
"""

import pymysql
import pytest

from tests.migration_helpers import SQUASHED, _migrate, _recreate, _run



def _insert(name, unit, kind, answer, decimals):
    _run("INSERT INTO meter_types (name, unit, kind, expected_answer, decimals, created_by)"
         " VALUES (%s, %s, %s, %s, %s, 'kla')", (name, unit, kind, answer, decimals))


def test_the_name_is_unique_whatever_its_case():
    _recreate()
    _migrate(SQUASHED)
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
    _migrate(SQUASHED)
    with pytest.raises(pymysql.err.OperationalError) as exc:
        _insert(*row)
    assert exc.value.args[0] == 4025 and "chk_meter_types_yes_no" in str(exc.value), why


def test_the_check_accepts_a_well_formed_yes_no_row_and_refuses_decimals_over_3():
    _recreate()
    _migrate(SQUASHED)
    _insert("Oil level above min", None, "yes_no", "yes", 0)
    with pytest.raises(pymysql.err.OperationalError) as exc:
        _insert("Pressure", "bar", "gauge", None, 4)
    assert exc.value.args[0] == 4025 and "chk_meter_types_decimals" in str(exc.value)


