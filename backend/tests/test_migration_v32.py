"""v32, meter readings (S039 § 4, § 8) — now part of the squashed v41 (S088), in the upgrade database
UPGRADE_DB (one per test run and worker, tests/db_names.py).  The database keeps the reading's links and
its lists.  The upgrade from v31, the fresh-shape check and the re-run went with S088 (§ 8.2): the squash
test (test_migration_squash_v41.py) compares the whole schema and the seed rows with the old texts.
Needs the dev MariaDB container.
"""

import pymysql
import pytest

from tests.migration_helpers import SQUASHED, _migrate, _recreate, _run
from tests.test_migration_v22 import _fill_one_ticket



ER_NO_REFERENCED_ROW = 1452
ER_TRUNCATED = 1265   # an ENUM value outside the list (strict mode)


def _insert_reading(equipment_id, meter_type_id, **columns):
    values = {"equipment_id": equipment_id, "meter_type_id": meter_type_id, "value": "12345.6",
              "taken_at": "2026-10-23 18:00:00", "created_by": "kla", **columns}
    _run(f"INSERT INTO meter_readings ({', '.join(values)}) VALUES ({', '.join(['%s'] * len(values))})",
         tuple(values.values()))


def test_the_database_keeps_the_links_and_the_lists():
    _recreate()
    _migrate(SQUASHED)
    _fill_one_ticket()
    node = _run("SELECT id FROM equipment")[0]["id"]
    hours = _run("SELECT id FROM meter_types WHERE name = 'Run hours'")[0]["id"]
    _insert_reading(node, hours)
    row = _run("SELECT value, is_reset, limit_state, source, removed_at FROM meter_readings")[0]
    assert (str(row["value"]), row["is_reset"], row["limit_state"], row["source"], row["removed_at"]) == (
        "12345.600", 0, None, "manual", None)
    # Two readings may share a minute (a removed one and its replacement): no unique key
    _insert_reading(node, hours, removed_at="2026-10-23 18:05:00", removed_by="kla")
    assert _run("SELECT COUNT(*) AS n FROM meter_readings")[0]["n"] == 2
    with pytest.raises(pymysql.err.IntegrityError) as refused:
        _insert_reading(node, 999999)
    assert refused.value.args[0] == ER_NO_REFERENCED_ROW
    with pytest.raises(pymysql.err.DataError) as refused:
        _insert_reading(node, hours, limit_state="ok")
    assert refused.value.args[0] == ER_TRUNCATED


