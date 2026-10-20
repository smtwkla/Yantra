"""Migration v11: failure modes, causes and maintenance actions, with the ISO 14224 seed rows
(S016 § 4).  On the test DB: db_version 11 is removed and init_db runs twice; every statement
is a no-op on re-run, and an engineer's edit of a seed row is kept.  Seed rows are counted by
created_by, so rows other tests add never change the counts.
"""

import config
from local_db import get_local_db, init_db
from tests.conftest import SEED_CREATOR


def _run(sql, params=()):
    conn = get_local_db(config.DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()
    finally:
        conn.close()


def _columns(table):
    return {r["COLUMN_NAME"]: (r["COLUMN_TYPE"], r["IS_NULLABLE"]) for r in _run(
        "SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s", (table,))}


def _unique_keys(table):
    rows = _run("SELECT INDEX_NAME, COLUMN_NAME FROM information_schema.STATISTICS WHERE TABLE_SCHEMA = DATABASE() "
                "AND TABLE_NAME = %s AND NON_UNIQUE = 0 AND INDEX_NAME <> 'PRIMARY' ORDER BY INDEX_NAME, SEQ_IN_INDEX",
                (table,))
    keys = {}
    for r in rows:
        keys.setdefault(r["INDEX_NAME"], []).append(r["COLUMN_NAME"])
    return keys


def _seed_count(table):
    return _run(f"SELECT COUNT(*) AS n FROM {table} WHERE created_by = %s", (SEED_CREATOR,))[0]["n"]


def _seed_rows(table):
    return _run(f"SELECT code, label, active FROM {table} WHERE created_by = %s ORDER BY code", (SEED_CREATOR,))


_TABLES = ("failure_modes", "failure_causes", "maintenance_actions")


def test_tables_and_their_unique_keys():
    modes = _columns("failure_modes")
    assert modes["code"] == ("varchar(8)", "NO") and modes["label"] == ("varchar(60)", "NO")
    assert modes["description"] == ("varchar(255)", "YES") and modes["class_id"] == ("int(11)", "YES")
    causes = _columns("failure_causes")
    assert causes["cause_group"] == ("enum('design','fabrication','operation','management','misc')", "NO")
    assert {"created_at", "created_by", "updated_at", "updated_by", "active"} <= set(_columns("maintenance_actions"))
    assert _unique_keys("failure_modes") == {"uq_failure_modes_code": ["code"]}
    assert _unique_keys("failure_causes") == {"uq_failure_causes_code": ["code"], "uq_failure_causes_label": ["label"]}
    assert _unique_keys("maintenance_actions") == {"uq_maintenance_actions_code": ["code"],
                                                   "uq_maintenance_actions_label": ["label"]}
    picker = _run("SELECT COLUMN_NAME FROM information_schema.STATISTICS WHERE TABLE_SCHEMA = DATABASE() "
                  "AND TABLE_NAME = 'failure_modes' AND INDEX_NAME = 'ix_failure_modes_class' ORDER BY SEQ_IN_INDEX")
    assert [r["COLUMN_NAME"] for r in picker] == ["class_id", "active"]
    fk = _run("SELECT REFERENCED_TABLE_NAME FROM information_schema.KEY_COLUMN_USAGE WHERE TABLE_SCHEMA = DATABASE() "
              "AND TABLE_NAME = 'failure_modes' AND COLUMN_NAME = 'class_id' AND REFERENCED_TABLE_NAME IS NOT NULL")
    assert [r["REFERENCED_TABLE_NAME"] for r in fk] == ["equipment_classes"]


def test_seed_rows():
    assert (_seed_count("failure_modes"), _seed_count("failure_causes"), _seed_count("maintenance_actions")) == (
        14, 15, 12)
    # Every seed mode is General
    assert _run("SELECT COUNT(*) AS n FROM failure_modes WHERE created_by = %s AND class_id IS NOT NULL",
                (SEED_CREATOR,))[0]["n"] == 0
    noise = _run("SELECT label, description FROM failure_modes WHERE code = 'NOI'")[0]
    assert noise == {"label": "Abnormal noise", "description": "Noise"}
    brd = _run("SELECT label FROM failure_modes WHERE code = 'BRD'")[0]
    assert brd["label"] == "Stopped, won't run"
    groups = _run("SELECT cause_group, COUNT(*) AS n FROM failure_causes WHERE created_by = %s "
                  "GROUP BY cause_group ORDER BY cause_group", (SEED_CREATOR,))
    assert [(r["cause_group"], r["n"]) for r in groups] == [
        ("design", 2), ("fabrication", 2), ("operation", 4), ("management", 2), ("misc", 5)]
    actions = _run("SELECT code FROM maintenance_actions WHERE created_by = %s ORDER BY CHAR_LENGTH(code), code",
                   (SEED_CREATOR,))
    assert [r["code"] for r in actions] == [str(n) for n in range(1, 13)]


def test_rerun_changes_nothing_and_keeps_an_edited_seed_row():
    _run("UPDATE failure_modes SET label = 'Noisy', active = 0 WHERE code = 'NOI'")
    try:
        before = {table: (_columns(table), _seed_rows(table)) for table in _TABLES}
        for _ in range(2):
            _run("DELETE FROM db_version WHERE version = 11")
            init_db(config.DB_CONFIG)
        assert {table: (_columns(table), _seed_rows(table)) for table in _TABLES} == before
        assert _run("SELECT version FROM db_version WHERE version = 11")
        assert _run("SELECT label, active FROM failure_modes WHERE code = 'NOI'")[0] == {"label": "Noisy", "active": 0}
    finally:
        _run("UPDATE failure_modes SET label = 'Abnormal noise', active = 1 WHERE code = 'NOI'")
