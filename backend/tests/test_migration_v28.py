"""v28, model optional on component units (S033 § 4), in the upgrade database UPGRADE_DB that the
v20-v27 migration tests also use (one per test run and worker, tests/db_names.py).  A v27 database
with a machine keeps its row; after v28 equipment.model_id is NULLable and the CHECK refuses an
equipment-level row without a model but accepts a component unit; a re-run changes nothing.
Needs the dev MariaDB container.
"""

import pymysql
import pytest

import local_db
from tests.test_migration_v20 import _migrate, _recreate, _run, _schema
from tests.test_migration_v22 import _fill_one_ticket

V27 = [m for m in local_db._MIGRATIONS if m[0] in (20, 21, 22, 23, 24, 25, 26, 27)]
V28 = [m for m in local_db._MIGRATIONS if m[0] in (20, 21, 22, 23, 24, 25, 26, 27, 28)]
VERSIONS = [20, 21, 22, 23, 24, 25, 26, 27, 28]


def _versions():
    return [r["version"] for r in _run("SELECT version FROM db_version ORDER BY version")]


def _model_id_nullable():
    rows = _run("SELECT IS_NULLABLE FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE()"
                " AND TABLE_NAME = 'equipment' AND COLUMN_NAME = 'model_id'")
    return rows[0]["IS_NULLABLE"] == "YES"


def _insert_node(code, level, model_sql):
    """A node under the machine HP001 (or, for level equipment, in its unit), of the press class."""
    place = ("u.id, NULL" if level == "equipment" else "NULL, e.id")
    _run("INSERT INTO equipment (code, level, unit_id, parent_id, class_id, model_id, name, created_by)"
         f" SELECT %s, %s, {place}, e.class_id, {model_sql}, 'Node', 'kla'"
         " FROM equipment e JOIN units u ON u.id = e.unit_id WHERE e.code = 'HP001'", (code, level))


def test_a_v27_database_gets_v28_and_keeps_its_rows():
    _recreate()
    _migrate(V27)
    _fill_one_ticket()
    before = _run("SELECT * FROM equipment ORDER BY id")
    assert not _model_id_nullable()

    _migrate(V28)
    assert _versions() == VERSIONS
    assert _model_id_nullable()
    assert _run("SELECT * FROM equipment ORDER BY id") == before


@pytest.mark.parametrize("level", ["equipment", "component"])
def test_the_check_refuses_equipment_or_a_component_without_a_model(level):
    _recreate()
    _migrate(V28)
    _fill_one_ticket()
    with pytest.raises(pymysql.err.OperationalError) as exc:
        _insert_node("HP002", level, "NULL")
    assert "chk_equipment_model_level" in str(exc.value)


def test_the_check_accepts_a_component_unit_without_a_model_and_the_fk_still_holds():
    _recreate()
    _migrate(V28)
    _fill_one_ticket()
    _insert_node("HP002", "component_unit", "NULL")
    assert _run("SELECT model_id FROM equipment WHERE code = 'HP002'") == [{"model_id": None}]
    # A model still has to match the node's class (fk_equipment_model)
    _run("INSERT INTO equipment_classes (code, name, created_by) VALUES ('GB', 'Gearbox', 'kla')")
    _run("INSERT INTO equipment_models (manufacturer_id, designation, class_id, created_by)"
         " SELECT m.id, 'GB-1', c.id, 'kla' FROM manufacturers m, equipment_classes c WHERE c.code = 'GB'")
    with pytest.raises(pymysql.err.IntegrityError):
        _insert_node("HP003", "component_unit", "(SELECT id FROM equipment_models WHERE designation = 'GB-1')")


def test_running_v28_again_changes_nothing():
    _recreate()
    _migrate(V28)
    schema = _schema()
    _run("DELETE FROM db_version WHERE version = 28")
    _migrate(V28)
    assert _versions() == VERSIONS
    assert _schema() == schema
