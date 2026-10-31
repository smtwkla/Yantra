"""v33, an equipment item's own property values (S044 § 4, § 8.3) — now part of the squashed v41 (S088), in
the upgrade database UPGRADE_DB (one per test run and worker, tests/db_names.py).  The database keeps one
value and the option's property.  The upgrade from v32, the fresh-shape check and the re-run went with
S088 (§ 8.2): the squash test (test_migration_squash_v41.py) compares the whole schema and the seed rows
with the old texts.  Needs the dev MariaDB container.
"""

import pymysql
import pytest

from tests.migration_helpers import SQUASHED, _migrate, _recreate, _run
from tests.test_migration_v22 import _fill_one_ticket



NEW_TABLE = "equipment_property_values"
ER_NO_REFERENCED_ROW = 1452
ER_CHECK_CONSTRAINT = 4025
ER_TRUNCATED = 1265   # an ENUM value outside the list (strict mode)


def _property(name):
    return _run("SELECT id FROM property_definitions WHERE name = %s", (name,))[0]["id"]


def _insert_value(equipment_id, property_id, **columns):
    values = {"equipment_id": equipment_id, "property_id": property_id, **columns}
    _run(f"INSERT INTO {NEW_TABLE} ({', '.join(values)}) VALUES ({', '.join(['%s'] * len(values))})",
         tuple(values.values()))


def _event(equipment_id, event):
    _run("INSERT INTO equipment_events (equipment_id, event, old_value, new_value, created_by)"
         " VALUES (%s, %s, 'a', 'b', 'kla')", (equipment_id, event))


def test_the_database_keeps_one_value_and_the_option_s_property():
    _recreate()
    _migrate(SQUASHED)
    _fill_one_ticket()
    node = _run("SELECT id FROM equipment")[0]["id"]
    frame, orientation, sealing = _property("Frame size"), _property("Shaft orientation"), _property("Shaft sealing")
    _insert_value(node, frame, value_text="132M")
    assert _run(f"SELECT value_text FROM {NEW_TABLE}")[0]["value_text"] == "132M"
    # Exactly one value column filled
    for columns in ({}, {"value_text": "x", "value_number": 1}):
        with pytest.raises(pymysql.err.OperationalError) as refused:
            _insert_value(node, _property("Speed"), **columns)
        assert refused.value.args[0] == ER_CHECK_CONSTRAINT
    # The option must be this property's (the composite FK)
    sealing_option = _run("SELECT id FROM property_options WHERE property_id = %s LIMIT 1", (sealing,))[0]["id"]
    with pytest.raises(pymysql.err.IntegrityError) as refused:
        _insert_value(node, orientation, option_id=sealing_option)
    assert refused.value.args[0] == ER_NO_REFERENCED_ROW
    with pytest.raises(pymysql.err.IntegrityError) as refused:
        _insert_value(999999, frame, value_text="x")
    assert refused.value.args[0] == ER_NO_REFERENCED_ROW
    _event(node, "property")
    with pytest.raises(pymysql.err.DataError) as refused:
        _event(node, "nameplate")
    assert refused.value.args[0] == ER_TRUNCATED


