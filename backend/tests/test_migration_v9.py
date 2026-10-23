"""Manufacturers, equipment models, equipment.model_id NOT NULL, model documents (S012 § 4) —
built by v9, now by v20 (S025: v1–v13 squashed; v20's re-run is test_migration_v20.py's).
Tests of today's schema.  Needs the dev MariaDB container (tooling/dev/dev-db-up.bat).
"""

import pymysql
import pytest

import config
from local_db import get_local_db


def _run(sql, params=()):
    conn = get_local_db(config.DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()
    finally:
        conn.close()


def _columns(table):
    return {r["COLUMN_NAME"]: r for r in _run(
        "SELECT COLUMN_NAME, IS_NULLABLE, COLUMN_TYPE FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s", (table,))}


def test_the_shape_holds():
    equipment = _columns("equipment")
    assert "make" not in equipment and "model" not in equipment
    assert equipment["model_id"]["IS_NULLABLE"] == "NO"
    assert _columns("equipment_documents")["equipment_id"]["IS_NULLABLE"] == "YES"
    # 'status' is 'lifecycle' since v25 (S030)
    assert _columns("equipment_events")["event"]["COLUMN_TYPE"] == (
        "enum('created','moved_unit','moved_parent','lifecycle','criticality','class','type','model')")


def test_an_equipment_row_with_a_null_model_is_refused(make_equipment):
    row = _run("SELECT unit_id, class_id FROM equipment WHERE id = %s", (make_equipment()["id"],))[0]
    with pytest.raises(pymysql.err.IntegrityError) as caught:
        _run("INSERT INTO equipment (code, level, unit_id, class_id, model_id, name, created_by) "
             "VALUES ('ZZV9N1', 'equipment', %s, %s, NULL, 'x', 'test')", (row["unit_id"], row["class_id"]))
    assert caught.value.args[0] == 1048


@pytest.mark.parametrize("owners", ["two", "none"])
def test_the_owner_check_refuses_two_owners_and_none(make_model, make_equipment, uniq, owners):
    model = make_model()
    node = make_equipment(model=model)
    equipment_id, model_id = (node["id"], model["id"]) if owners == "two" else (None, None)
    with pytest.raises(pymysql.err.OperationalError) as caught:
        _run("INSERT INTO equipment_documents (equipment_id, model_id, kind, title, original_name, stored_name,"
             " content_type, size_bytes, created_by) VALUES (%s, %s, 'document', 'x', 'x.pdf', %s,"
             " 'application/pdf', 1, 'test')", (equipment_id, model_id, f"v9-{uniq.username()}.pdf"))
    assert caught.value.args[0] == 4025
