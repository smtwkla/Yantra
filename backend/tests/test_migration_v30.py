"""v30, meters on models and equipment (S038 § 4), in the upgrade database UPGRADE_DB that the
v20-v29 migration tests also use (one per test run and worker, tests/db_names.py).  A v29 database
with a machine and one history line of every v25 event keeps those rows; after v30 the two link
tables exist, the ENUM takes the three meter events, the unique keys and the limits CHECKs hold,
and a re-run changes nothing.  Needs the dev MariaDB container.
"""

import pymysql
import pytest

import local_db
from tests.test_migration_v20 import _migrate, _recreate, _run, _schema
from tests.test_migration_v22 import _fill_one_ticket

V29 = [m for m in local_db._MIGRATIONS if m[0] in range(20, 30)]
V30 = [m for m in local_db._MIGRATIONS if m[0] in range(20, 31)]
VERSIONS = list(range(20, 31))
OLD_EVENTS = ["created", "moved_unit", "moved_parent", "lifecycle", "criticality", "class", "type", "model"]


def _versions():
    return [r["version"] for r in _run("SELECT version FROM db_version ORDER BY version")]


def _tables():
    rows = _run("SELECT TABLE_NAME AS t FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE()"
                " AND TABLE_NAME IN ('model_meters', 'node_meters') ORDER BY TABLE_NAME")
    return [r["t"] for r in rows]


def _add_event(event):
    _run("INSERT INTO equipment_events (equipment_id, event, old_value, new_value, created_by)"
         " SELECT id, %s, 'old', 'new', 'kla' FROM equipment WHERE code = 'HP001'", (event,))


def _model_meter(min_value, max_value, type_name="Oil temperature"):
    _run("INSERT INTO model_meters (model_id, meter_type_id, min_value, max_value, created_by)"
         " SELECT m.id, t.id, %s, %s, 'kla' FROM equipment_models m, meter_types t WHERE t.name = %s",
         (min_value, max_value, type_name))


def _node_meter(own, min_value, max_value, type_name="Oil temperature"):
    _run("INSERT INTO node_meters (equipment_id, meter_type_id, own, min_value, max_value, created_by)"
         " SELECT e.id, t.id, %s, %s, %s, 'kla' FROM equipment e, meter_types t"
         " WHERE e.code = 'HP001' AND t.name = %s", (own, min_value, max_value, type_name))


def test_a_v29_database_gets_v30_and_keeps_every_event_row():
    _recreate()
    _migrate(V29)
    _fill_one_ticket()
    for event in OLD_EVENTS:
        _add_event(event)
    before = _run("SELECT * FROM equipment_events ORDER BY id")
    assert _tables() == []

    _migrate(V30)
    assert _versions() == VERSIONS
    assert _tables() == ["model_meters", "node_meters"]
    assert _run("SELECT * FROM equipment_events ORDER BY id") == before
    for event in ("meter_added", "meter_removed", "meter_limits"):
        _add_event(event)
    assert [r["event"] for r in _run("SELECT event FROM equipment_events ORDER BY id")] == \
        OLD_EVENTS + ["meter_added", "meter_removed", "meter_limits"]


def test_one_meter_of_a_type_per_model_and_per_node():
    _recreate()
    _migrate(V30)
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
    _migrate(V30)
    _fill_one_ticket()
    insert = _model_meter if table == "model_meters" else (lambda lo, hi, **kw: _node_meter(1, lo, hi, **kw))
    with pytest.raises(pymysql.err.OperationalError) as exc:
        insert("60", "10")
    assert exc.value.args[0] == 4025 and f"chk_{table}_limits" in str(exc.value)
    insert(None, "60")
    insert("10", None, type_name="Fuel level")
    insert("10", "10", type_name="Energy")
    assert _run(f"SELECT COUNT(*) AS n FROM {table}") == [{"n": 3}]


def test_running_v30_again_changes_nothing():
    _recreate()
    _migrate(V30)
    _fill_one_ticket()
    _model_meter("10", "60")
    schema, rows = _schema(), _run("SELECT * FROM model_meters")
    _run("DELETE FROM db_version WHERE version = 30")
    _migrate(V30)
    assert _versions() == VERSIONS
    assert _schema() == schema
    assert _run("SELECT * FROM model_meters") == rows
