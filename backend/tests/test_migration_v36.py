"""v36, improvements and their tickets (S067 § 4.1, § 8.1) — now part of the squashed v41 (S088), in the
upgrade database UPGRADE_DB (one per test run and worker, tests/db_names.py).  The unique key allows one
open link per ticket and any number of closed (NULL) ones; the CHECK refuses another open_link value.
The upgrade from v35, the fresh-shape check and the re-run went with S088 (§ 8.2): the squash test
(test_migration_squash_v41.py) compares the whole schema and the seed rows with the old texts.  Needs the
dev MariaDB container.
"""

import pymysql
import pytest

from tests.migration_helpers import SQUASHED, _migrate, _recreate, _run
from tests.test_migration_v22 import _fill_one_ticket



ER_DUP_ENTRY = 1062
ER_CONSTRAINT_FAILED = 4025


def _keys(table):
    return _run("SELECT INDEX_NAME, NON_UNIQUE, GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX) AS cols"
                " FROM information_schema.STATISTICS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s"
                " GROUP BY INDEX_NAME, NON_UNIQUE ORDER BY INDEX_NAME", (table,))


def _foreign_keys(table):
    return _run("SELECT CONSTRAINT_NAME, REFERENCED_TABLE_NAME FROM information_schema.REFERENTIAL_CONSTRAINTS"
                " WHERE CONSTRAINT_SCHEMA = DATABASE() AND TABLE_NAME = %s ORDER BY CONSTRAINT_NAME", (table,))


def _one_improvement():
    """An improvement on the one ticket of _fill_one_ticket, led by a person; -> its id."""
    _run("INSERT INTO people (name, employment, created_by) VALUES ('Lead', 'direct', 'kla')")
    _run("INSERT INTO improvements (serial, unit_id, equipment_id, title, problem, lead_id, created_by)"
         " SELECT 'IM-2026-10-001', t.unit_id, t.equipment_id, 'Dust', 'Dust in the panel', p.id, 'kla'"
         " FROM tickets t, people p")
    return _run("SELECT id FROM improvements")[0]["id"]


def _link(improvement_id, ticket_id, open_link):
    _run("INSERT INTO improvement_tickets (improvement_id, ticket_id, open_link, created_by)"
         " VALUES (%s, %s, %s, 'kla')",
         (improvement_id, ticket_id, open_link))


def test_one_open_link_per_ticket_and_any_number_of_closed_ones():
    """D4: MariaDB's unique index treats NULLs as distinct, so a ticket may sit in many closed
    improvements (open_link NULL) and in only one open one (open_link 1)."""
    _recreate()
    _migrate(SQUASHED)
    _fill_one_ticket()
    first = _one_improvement()
    _run("INSERT INTO improvements (serial, unit_id, equipment_id, title, problem, lead_id, created_by)"
         " SELECT 'IM-2026-10-002', unit_id, equipment_id, title, problem, lead_id, 'kla' FROM improvements")
    _run("INSERT INTO improvements (serial, unit_id, equipment_id, title, problem, lead_id, created_by)"
         " SELECT 'IM-2026-10-003', unit_id, equipment_id, title, problem, lead_id, 'kla' FROM improvements"
         " WHERE serial = 'IM-2026-10-001'")
    second, third = [r["id"] for r in _run("SELECT id FROM improvements WHERE id <> %s ORDER BY id", (first,))]
    ticket_id = _run("SELECT id FROM tickets")[0]["id"]

    _link(first, ticket_id, 1)
    with pytest.raises(pymysql.err.IntegrityError) as refused:
        _link(second, ticket_id, 1)
    assert refused.value.args[0] == ER_DUP_ENTRY
    assert "uq_improvement_tickets_open" in refused.value.args[1]

    _link(second, ticket_id, None)
    _link(third, ticket_id, None)
    assert _run("SELECT COUNT(*) AS n FROM improvement_tickets WHERE ticket_id = %s", (ticket_id,)) == [{"n": 3}]


def test_the_check_refuses_another_open_link_value():
    _recreate()
    _migrate(SQUASHED)
    _fill_one_ticket()
    improvement_id = _one_improvement()
    with pytest.raises(pymysql.err.OperationalError) as refused:
        _link(improvement_id, _run("SELECT id FROM tickets")[0]["id"], 2)
    assert refused.value.args[0] == ER_CONSTRAINT_FAILED


