"""v28, model optional on component units (S033 § 4) — now part of the squashed v41 (S088), in the upgrade
database UPGRADE_DB (one per test run and worker, tests/db_names.py).  equipment.model_id is NULLable;
the CHECK refuses an equipment-level row without a model but accepts a component unit.  The upgrade from
v27, the fresh-shape check and the re-run went with S088 (§ 8.2): the squash test
(test_migration_squash_v41.py) compares the whole schema and the seed rows with the old texts.  Needs the
dev MariaDB container.
"""

import pymysql
import pytest

from tests.migration_helpers import SQUASHED, _migrate, _recreate, _run
from tests.test_migration_v22 import _fill_one_ticket



def _insert_node(code, level, model_sql):
    """A node under the machine HP001 (or, for level equipment, in its unit), of the press class."""
    place = ("u.id, NULL" if level == "equipment" else "NULL, e.id")
    _run("INSERT INTO equipment (code, level, unit_id, parent_id, class_id, model_id, name, created_by)"
         f" SELECT %s, %s, {place}, e.class_id, {model_sql}, 'Node', 'kla'"
         " FROM equipment e JOIN units u ON u.id = e.unit_id WHERE e.code = 'HP001'", (code, level))


@pytest.mark.parametrize("level", ["equipment", "component"])
def test_the_check_refuses_equipment_or_a_component_without_a_model(level):
    _recreate()
    _migrate(SQUASHED)
    _fill_one_ticket()
    with pytest.raises(pymysql.err.OperationalError) as exc:
        _insert_node("HP002", level, "NULL")
    assert "chk_equipment_model_level" in str(exc.value)


def test_the_check_accepts_a_component_unit_without_a_model_and_the_fk_still_holds():
    _recreate()
    _migrate(SQUASHED)
    _fill_one_ticket()
    _insert_node("HP002", "component_unit", "NULL")
    assert _run("SELECT model_id FROM equipment WHERE code = 'HP002'") == [{"model_id": None}]
    # A model still has to match the node's class (fk_equipment_model)
    _run("INSERT INTO equipment_classes (code, name, created_by) VALUES ('GB', 'Gearbox', 'kla')")
    _run("INSERT INTO equipment_models (manufacturer_id, designation, class_id, created_by)"
         " SELECT m.id, 'GB-1', c.id, 'kla' FROM manufacturers m, equipment_classes c WHERE c.code = 'GB'")
    with pytest.raises(pymysql.err.IntegrityError):
        _insert_node("HP003", "component_unit", "(SELECT id FROM equipment_models WHERE designation = 'GB-1')")


