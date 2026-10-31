"""v38, countermeasures and their photos (S070 § 4.1, § 8.1) — now part of the squashed v41 (S088), in the
upgrade database UPGRADE_DB (one per test run and worker, tests/db_names.py).  The CHECKs keep a done or
cancelled row whole.  The four-owner document test went with S088: v41 counts five owners
(test_migration_v41.py).  The upgrade from v37, the fresh-shape check and the re-run went with S088
(§ 8.2): the squash test (test_migration_squash_v41.py) compares the whole schema and the seed rows with
the old texts.  Needs the dev MariaDB container.
"""

import pymysql
import pytest

from tests.migration_helpers import SQUASHED, _migrate, _recreate, _run
from tests.test_migration_v22 import _fill_one_ticket
from tests.test_migration_v36 import _one_improvement



ER_CONSTRAINT_FAILED = 4025


def _add_document(column, owner_id, name, action_id=None):
    """A document row of one owner (``column``), and optionally action_id too (two owners; v38 only)."""
    columns, values = [column], [owner_id]
    if action_id is not None:
        columns.append("action_id")
        values.append(action_id)
    _run(f"INSERT INTO equipment_documents ({', '.join(columns)}, kind, title, original_name, stored_name,"
         f" content_type, size_bytes, created_by) VALUES ({', '.join(['%s'] * len(values))}, 'photo', 'x', 'x.jpg',"
         " %s, 'image/jpeg', 1, 'kla')", (*values, name))


def _documents_of_three_owners():
    """A node's, a model's and a ticket's document, as production holds them."""
    node = _run("SELECT id, model_id FROM equipment")[0]
    ticket_id = _run("SELECT id FROM tickets")[0]["id"]
    _add_document("equipment_id", node["id"], "node.jpg")
    _add_document("model_id", node["model_id"], "model.jpg")
    _add_document("ticket_id", ticket_id, "ticket.jpg")


def _add_action(improvement_id, state="open", done=(None, None, None), cancelled=(None, None, None)):
    _run("INSERT INTO improvement_actions (improvement_id, kind, text, owner_id, due_date, state, done_text, done_at,"
         " done_by, cancel_reason, cancelled_at, cancelled_by, created_by)"
         " SELECT %s, 'corrective', 'Seal the panel', p.id, '2026-11-15', %s, %s, %s, %s, %s, %s, %s, 'kla'"
         " FROM people p ORDER BY p.id LIMIT 1", (improvement_id, state, *done, *cancelled))
    return _run("SELECT MAX(id) AS id FROM improvement_actions")[0]["id"]


def _owner_check_clause():
    return _run("SELECT CHECK_CLAUSE FROM information_schema.CHECK_CONSTRAINTS WHERE CONSTRAINT_SCHEMA = DATABASE()"
                " AND TABLE_NAME = 'equipment_documents' AND CONSTRAINT_NAME = 'chk_equipment_documents_owner'")


def test_the_checks_keep_done_and_cancelled_whole():
    _recreate()
    _migrate(SQUASHED)
    _fill_one_ticket()
    improvement_id = _one_improvement()
    done = ("Fitted", "2026-10-30 10:00:00", "kla")
    cancelled = ("Duplicate", "2026-10-30 10:00:00", "kla")
    for state, done_fields, cancel_fields in (
            ("done", (None, "2026-10-30 10:00:00", "kla"), (None, None, None)),   # done without its text
            ("open", done, (None, None, None)),                                    # open with all three
            ("cancelled", (None, None, None), (None, "2026-10-30 10:00:00", "kla")),
            ("open", (None, None, None), cancelled)):
        with pytest.raises(pymysql.err.OperationalError) as refused:
            _add_action(improvement_id, state, done_fields, cancel_fields)
        assert refused.value.args[0] == ER_CONSTRAINT_FAILED
    _add_action(improvement_id)
    _add_action(improvement_id, "done", done)
    _add_action(improvement_id, "cancelled", cancelled=cancelled)
    assert [r["state"] for r in _run("SELECT state FROM improvement_actions ORDER BY id")] == [
        "open", "done", "cancelled"]


