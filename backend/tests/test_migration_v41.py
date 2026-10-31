"""v41, one-point lessons and their photos (S075 § 4.1, § 8.1), the last version the squash holds — now part
of the squashed v41 (S088), in the upgrade database UPGRADE_DB (one per test run and worker,
tests/db_names.py).  The CHECK keeps a document to one of five owners; one lesson per countermeasure;
Tamil text is stored whole.  The upgrade from v40, the fresh-shape check and the re-run went with S088
(§ 8.2): the squash test (test_migration_squash_v41.py) compares the whole schema and the seed rows with
the old texts.  Needs the dev MariaDB container.
"""

import pymysql
import pytest

from tests.migration_helpers import SQUASHED, _migrate, _recreate, _run
from tests.test_migration_v22 import _fill_one_ticket
from tests.test_migration_v36 import _one_improvement
from tests.test_migration_v38 import _add_action, _add_document, _documents_of_three_owners



ER_CONSTRAINT_FAILED = 4025
ER_DUP_ENTRY = 1062


def _add_lesson(serial, action_id=None, title="Keep the panel door shut", body="Dust trips the contactor"):
    """A lesson on the one machine, for its class -> its id."""
    _run("INSERT INTO procedures (serial, equipment_id, class_id, title, body, action_id, created_by)"
         " SELECT %s, e.id, e.class_id, %s, %s, %s, 'kla' FROM equipment e ORDER BY e.id LIMIT 1",
         (serial, title, body, action_id))
    return _run("SELECT id FROM procedures WHERE serial = %s", (serial,))[0]["id"]


def _a_database_with_rows():
    """The squashed v41 with a ticket, an improvement, a countermeasure and documents of the four
    owners before the lesson -> the countermeasure's id."""
    _recreate()
    _migrate(SQUASHED)
    _fill_one_ticket()
    action_id = _add_action(_one_improvement())
    _documents_of_three_owners()
    _add_document("action_id", action_id, "action.jpg")
    return action_id


def test_a_document_has_exactly_one_of_five_owners():
    action_id = _a_database_with_rows()
    lesson_id = _add_lesson("OPL-001")
    _add_document("procedure_id", lesson_id, "lesson.jpg")
    with pytest.raises(pymysql.err.OperationalError) as refused:
        _run("INSERT INTO equipment_documents (action_id, procedure_id, kind, title, original_name, stored_name,"
             " content_type, size_bytes, created_by) VALUES (%s, %s, 'photo', 'x', 'x.jpg', 'two.jpg', 'image/jpeg',"
             " 1, 'kla')", (action_id, lesson_id))
    assert refused.value.args[0] == ER_CONSTRAINT_FAILED
    assert "chk_equipment_documents_owner" in refused.value.args[1]


def test_one_lesson_per_countermeasure_and_any_number_without_one():
    action_id = _a_database_with_rows()
    _add_lesson("OPL-001", action_id)
    with pytest.raises(pymysql.err.IntegrityError) as refused:
        _add_lesson("OPL-002", action_id)
    assert refused.value.args[0] == ER_DUP_ENTRY and "uq_procedures_action" in refused.value.args[1]
    _add_lesson("OPL-003")
    _add_lesson("OPL-004")
    assert _run("SELECT COUNT(*) AS n FROM procedures WHERE action_id IS NULL") == [{"n": 2}]


def test_tamil_text_at_the_bounds_is_stored_whole():
    """VARCHAR counts characters (code points), as Python's len: a Tamil letter with a vowel sign is two."""
    _a_database_with_rows()
    title, body = "கொ" * 40, "வரி" * 333 + "க"
    assert (len(title), len(body)) == (80, 1000)
    lesson_id = _add_lesson("OPL-001", title=title, body=body)
    assert _run("SELECT title, body FROM procedures WHERE id = %s", (lesson_id,)) == [{"title": title, "body": body}]


