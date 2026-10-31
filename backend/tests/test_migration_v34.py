"""v34, properties for every class, per-machine values and the Location type (S061 § 4, § 8.3) — now part of
the squashed v41 (S088), in the upgrade database UPGRADE_DB (one per test run and worker,
tests/db_names.py).  The CHECKs refuse a broken location.  The old precondition (a hand-made "GPS
location") went with its version.  The upgrade from v33, the fresh-shape check and the re-run went with
S088 (§ 8.2): the squash test (test_migration_squash_v41.py) compares the whole schema and the seed rows
with the old texts.  Needs the dev MariaDB container.
"""

from decimal import Decimal

import pymysql
import pytest

from tests.migration_helpers import SQUASHED, _migrate, _recreate, _run
from tests.test_migration_v22 import _fill_one_ticket



ER_CHECK_CONSTRAINT = 4025


def _property(name):
    return _run("SELECT id FROM property_definitions WHERE name = %s", (name,))[0]["id"]


def _insert(table, owner_column, owner_id, property_id, **columns):
    values = {owner_column: owner_id, "property_id": property_id, **columns}
    _run(f"INSERT INTO {table} ({', '.join(values)}) VALUES ({', '.join(['%s'] * len(values))})",
         tuple(values.values()))


def test_the_checks_refuse_a_broken_location():
    _recreate()
    _migrate(SQUASHED)
    _fill_one_ticket()
    node = _run("SELECT id FROM equipment")[0]["id"]
    model = _run("SELECT id FROM equipment_models")[0]["id"]
    gps = _property("GPS location")
    _insert("equipment_property_values", "equipment_id", node, gps, value_lat="11.016823", value_lng="76.955812")
    assert _run("SELECT value_lat, value_lng FROM equipment_property_values")[0] == {
        "value_lat": Decimal("11.016823"), "value_lng": Decimal("76.955812")}
    _insert("model_property_values", "model_id", model, gps, value_lat="-90", value_lng="180")
    refused_rows = (
        {"value_lat": "11"},                                     # a latitude without a longitude
        {"value_lng": "76"},                                     # a longitude without a latitude
        {"value_lat": "11", "value_lng": "76", "value_text": "x"},   # two value slots
        {"value_lat": "91", "value_lng": "76"},                  # out of range
        {"value_lat": "11", "value_lng": "-180.5"},
    )
    for columns in refused_rows:
        for table, owner_column, owner_id in (("equipment_property_values", "equipment_id", node),
                                              ("model_property_values", "model_id", model)):
            with pytest.raises(pymysql.err.OperationalError) as refused:
                _insert(table, owner_column, owner_id, _property("Speed"), **columns)
            assert refused.value.args[0] == ER_CHECK_CONSTRAINT, (table, columns)


