"""v30, meters on models and equipment (S038 § 4) — now part of the squashed v41 (S088), in the upgrade
database UPGRADE_DB (one per test run and worker, tests/db_names.py).  One meter of a type per model and
per node; the limits CHECKs refuse min above max.  The upgrade from v29, the fresh-shape check and the
re-run went with S088 (§ 8.2): the squash test (test_migration_squash_v41.py) compares the whole schema
and the seed rows with the old texts.  Needs the dev MariaDB container.
"""

import pymysql
import pytest

from tests.migration_helpers import SQUASHED, _migrate, _recreate, _run
from tests.test_migration_v22 import _fill_one_ticket



def _model_meter(min_value, max_value, type_name="Oil temperature"):
    _run("INSERT INTO model_meters (model_id, meter_type_id, min_value, max_value, created_by)"
         " SELECT m.id, t.id, %s, %s, 'kla' FROM equipment_models m, meter_types t WHERE t.name = %s",
         (min_value, max_value, type_name))


def _node_meter(own, min_value, max_value, type_name="Oil temperature"):
    _run("INSERT INTO node_meters (equipment_id, meter_type_id, own, min_value, max_value, created_by)"
         " SELECT e.id, t.id, %s, %s, %s, 'kla' FROM equipment e, meter_types t"
         " WHERE e.code = 'HP001' AND t.name = %s", (own, min_value, max_value, type_name))


def test_one_meter_of_a_type_per_model_and_per_node():
    _recreate()
    _migrate(SQUASHED)
    _fill_one_ticket()
    _model_meter("10", "60")
    _node_meter(0, "10", "55")
    with pytest.raises(pymysql.err.IntegrityError) as exc:
        _model_meter(None, None)
    assert "uq_model_meters" in str(exc.value)
    with pytest.raises(pymysql.err.IntegrityError) as exc:
        _node_meter(1, None, None)
    assert "uq_node_meters" in str(exc.value)


@pytest.mark.parametrize("table", ["model_meters", "node_meters"])
def test_the_limits_check_refuses_min_above_max_and_accepts_one_side(table):
    _recreate()
    _migrate(SQUASHED)
    _fill_one_ticket()
    insert = _model_meter if table == "model_meters" else (lambda lo, hi, **kw: _node_meter(1, lo, hi, **kw))
    with pytest.raises(pymysql.err.OperationalError) as exc:
        insert("60", "10")
    assert exc.value.args[0] == 4025 and f"chk_{table}_limits" in str(exc.value)
    insert(None, "60")
    insert("10", None, type_name="Fuel level")
    insert("10", "10", type_name="Energy")
    assert _run(f"SELECT COUNT(*) AS n FROM {table}") == [{"n": 3}]


