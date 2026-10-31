"""v35, equipment categories (S063 § 4.1, § 8.1) — now part of the squashed v41 (S088), in the upgrade
database UPGRADE_DB (one per test run and worker, tests/db_names.py).  The class's foreign key refuses an
unknown category.  The upgrade from v34, the fresh-shape check and the re-run went with S088 (§ 8.2): the
squash test (test_migration_squash_v41.py) compares the whole schema and the seed rows with the old
texts.  Needs the dev MariaDB container.
"""

import pymysql
import pytest

from tests.migration_helpers import SQUASHED, _migrate, _recreate, _run



ER_NO_REFERENCED_ROW = 1452


def test_the_key_refuses_an_unknown_category():
    _recreate()
    _migrate(SQUASHED)
    _run("INSERT INTO equipment_classes (code, name, created_by) VALUES ('KEY', 'Key test', 'kla')")
    with pytest.raises(pymysql.err.IntegrityError) as refused:
        _run("UPDATE equipment_classes SET category_id = 999 WHERE code = 'KEY'")
    assert refused.value.args[0] == ER_NO_REFERENCED_ROW


