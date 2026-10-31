"""v39, the states, the timeline and the verified close (S072 § 4.1, § 8.1) — now part of the squashed v41
(S088), in the upgrade database UPGRADE_DB (one per test run and worker, tests/db_names.py).  The CHECKs
keep the watch, the close and the follow-up whole; one follow-up per improvement.  The upgrade from v38,
the fresh-shape check and the re-run went with S088 (§ 8.2): the squash test
(test_migration_squash_v41.py) compares the whole schema and the seed rows with the old texts.  Needs the
dev MariaDB container.
"""

import pymysql
import pytest

from tests.migration_helpers import SQUASHED, _migrate, _recreate, _run
from tests.test_migration_v22 import _fill_one_ticket
from tests.test_migration_v36 import _one_improvement



ER_DUP_ENTRY = 1062
ER_CONSTRAINT_FAILED = 4025


def _another_improvement(serial):
    """A copy of the first improvement under another serial -> its id."""
    _run("INSERT INTO improvements (serial, unit_id, equipment_id, title, problem, lead_id, created_by)"
         " SELECT %s, unit_id, equipment_id, title, problem, lead_id, 'ravi' FROM improvements"
         " WHERE serial = 'IM-2026-10-001'", (serial,))
    return _run("SELECT id FROM improvements WHERE serial = %s", (serial,))[0]["id"]


@pytest.mark.parametrize("assignment, params", [
    ("watch_days = 29", ()),
    ("watch_days = 366", ()),
    ("state = 'watching'", ()),                                                    # watch_from NULL
    ("state = 'closed_effective', watch_from = NOW()", ()),                        # no closed_at
    ("state = 'dropped', closed_at = NOW(), closed_by = 'kla'", ()),               # no close_remark
    ("state = 'analysing', watch_from = NOW()", ()),
])
def test_the_checks(assignment, params):
    _recreate()
    _migrate(SQUASHED)
    _fill_one_ticket()
    improvement_id = _one_improvement()
    with pytest.raises(pymysql.err.OperationalError) as refused:
        _run(f"UPDATE improvements SET {assignment} WHERE id = %s", (*params, improvement_id))
    assert refused.value.args[0] == ER_CONSTRAINT_FAILED


def test_a_dropped_row_and_one_follow_up_per_improvement():
    _recreate()
    _migrate(SQUASHED)
    _fill_one_ticket()
    first = _one_improvement()
    _run("UPDATE improvements SET state = 'dropped', closed_at = NOW(), closed_by = 'kla', close_remark = 'No cause'"
         " WHERE id = %s", (first,))
    second = _another_improvement("IM-2026-10-002")
    third = _another_improvement("IM-2026-10-003")
    _run("UPDATE improvements SET follow_up_of_id = %s WHERE id = %s", (first, second))
    with pytest.raises(pymysql.err.IntegrityError) as refused:
        _run("UPDATE improvements SET follow_up_of_id = %s WHERE id = %s", (first, third))
    assert refused.value.args[0] == ER_DUP_ENTRY


