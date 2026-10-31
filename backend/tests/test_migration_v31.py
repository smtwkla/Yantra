"""v31, equipment properties (S043 § 4, § 8.3) — now part of the squashed v41 (S088), in the upgrade
database UPGRADE_DB (one per test run and worker, tests/db_names.py).  The database keeps the value
rules: one value column, the option's property.  The upgrade from v30, the fresh-shape check and the re-
run went with S088 (§ 8.2): the squash test (test_migration_squash_v41.py) compares the whole schema and
the seed rows with the old texts.  Needs the dev MariaDB container.
"""

import pymysql
import pytest

from tests.migration_helpers import SQUASHED, _migrate, _recreate, _run
from tests.test_migration_v22 import _fill_one_ticket



ER_CONSTRAINT_FAILED = 4025
ER_NO_REFERENCED_ROW = 1452


def test_the_database_keeps_the_value_rules():
    """The CHECKs and the option's composite FK hold even past the backend."""
    _recreate()
    _migrate(SQUASHED)
    _fill_one_ticket()
    with pytest.raises(pymysql.err.OperationalError) as refused:
        _run("UPDATE property_definitions SET unit = 'kW' WHERE name = 'Frame size'")
    assert refused.value.args[0] == ER_CONSTRAINT_FAILED

    model = _run("SELECT id FROM equipment_models")[0]["id"]
    power = _run("SELECT id FROM property_definitions WHERE name = 'Power – design'")[0]["id"]
    insert = ("INSERT INTO model_property_values (model_id, property_id, value_number, value_text, option_id)"
              " VALUES (%s, %s, %s, %s, %s)")
    for number, text in ((None, None), ("7.5", "x")):
        with pytest.raises(pymysql.err.OperationalError) as refused:
            _run(insert, (model, power, number, text, None))
        assert refused.value.args[0] == ER_CONSTRAINT_FAILED
    # An option of another property is refused by the composite FK
    vertical = _run("SELECT id FROM property_options WHERE label = 'Vertical'")[0]["id"]
    with pytest.raises(pymysql.err.IntegrityError) as refused:
        _run(insert, (model, power, None, None, vertical))
    assert refused.value.args[0] == ER_NO_REFERENCED_ROW
    _run(insert, (model, power, "7.5", None, None))
    assert str(_run("SELECT value_number FROM model_property_values")[0]["value_number"]) == "7.5000"


