"""v37, the why-why chain and the root cause (S069 § 4.1, § 8.1) — now part of the squashed v41 (S088), in
the upgrade database UPGRADE_DB (one per test run and worker, tests/db_names.py).  The CHECKs refuse a
root cause half set and a position 0.  The upgrade from v36, the fresh-shape check and the re-run went
with S088 (§ 8.2): the squash test (test_migration_squash_v41.py) compares the whole schema and the seed
rows with the old texts.  Needs the dev MariaDB container.
"""

import pymysql
import pytest

from tests.migration_helpers import SQUASHED, _migrate, _recreate, _run
from tests.test_migration_v22 import _fill_one_ticket
from tests.test_migration_v36 import _one_improvement



ER_CONSTRAINT_FAILED = 4025


def _cause_id(code):
    return _run("SELECT id FROM failure_causes WHERE code = %s", (code,))[0]["id"]


def _add_why(improvement_id, position):
    _run("INSERT INTO improvement_whys (improvement_id, position, question, answer, created_by)"
         " VALUES (%s, %s, 'Why?', 'Because', 'kla')", (improvement_id, position))


def _set_root_cause(improvement_id, text, cause_id):
    _run("UPDATE improvements SET root_cause = %s, root_cause_id = %s WHERE id = %s", (text, cause_id, improvement_id))


def test_the_checks_keep_the_root_cause_whole_and_positions_from_one():
    _recreate()
    _migrate(SQUASHED)
    _fill_one_ticket()
    improvement_id = _one_improvement()
    cause_id = _cause_id("4.2")
    for text, cause in (("No PM plan", None), (None, cause_id)):
        with pytest.raises(pymysql.err.OperationalError) as refused:
            _set_root_cause(improvement_id, text, cause)
        assert refused.value.args[0] == ER_CONSTRAINT_FAILED
    _set_root_cause(improvement_id, "No PM plan", cause_id)
    _set_root_cause(improvement_id, None, None)
    with pytest.raises(pymysql.err.OperationalError) as refused:
        _add_why(improvement_id, 0)
    assert refused.value.args[0] == ER_CONSTRAINT_FAILED
    _add_why(improvement_id, 1)
    assert _run("SELECT position FROM improvement_whys") == [{"position": 1}]


