"""access_log, task_queue, the internal_networks default (S013 § 4) — built by v10, now by v20
(S025: v1–v13 squashed).  The shape tests check today's schema; the re-run tests remove
db_version 20 and run init_db again: the setting's INSERT IGNORE keeps a stored value.
"""

import config
from local_db import get_local_db, init_db
from network_core import DEFAULT_INTERNAL_NETWORKS


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


def _setting():
    return _run("SELECT setting_value FROM app_settings WHERE setting_key = 'internal_networks'")[0]["setting_value"]


def test_tables_and_the_default():
    log = _columns("access_log")
    assert log["outcome"][0] == "enum('ok','auth_failed','denied_network','denied_perm')"
    assert log["client_ip"] == ("varchar(45)", "NO") and log["username"] == ("varchar(100)", "YES")
    # A1: one row per sighting per day, held by the database
    assert log["sighting_day"] == ("date", "NO") and log["sighting_hash"] == ("char(40)", "NO")
    unique = _run("SELECT COLUMN_NAME FROM information_schema.STATISTICS WHERE TABLE_SCHEMA = DATABASE() "
                  "AND TABLE_NAME = 'access_log' AND INDEX_NAME = 'ux_access_log_sighting' AND NON_UNIQUE = 0 "
                  "ORDER BY SEQ_IN_INDEX")
    assert [r["COLUMN_NAME"] for r in unique] == ["sighting_hash", "sighting_day"]
    queue = _columns("task_queue")
    assert queue["status"][0] == "enum('pending','running','done','failed')"
    assert {"scheduled_for", "locked_until", "last_error", "completed_at"} <= set(queue)
    # The log has no foreign keys: it keeps its rows when people or logins change
    assert not _run("SELECT 1 FROM information_schema.KEY_COLUMN_USAGE WHERE TABLE_SCHEMA = DATABASE() "
                    "AND TABLE_NAME = 'access_log' AND REFERENCED_TABLE_NAME IS NOT NULL")


def test_rerun_changes_nothing_and_keeps_a_stored_value():
    _run("UPDATE app_settings SET setting_value = '10.24.0.0/16' WHERE setting_key = 'internal_networks'")
    try:
        before = (_columns("access_log"), _columns("task_queue"))
        for _ in range(2):
            _run("DELETE FROM db_version WHERE version = 20")
            init_db(config.DB_CONFIG)
        assert (_columns("access_log"), _columns("task_queue")) == before
        assert _run("SELECT version FROM db_version WHERE version = 20")
        assert _setting() == "10.24.0.0/16"
    finally:
        _run("UPDATE app_settings SET setting_value = %s WHERE setting_key = 'internal_networks'",
             (DEFAULT_INTERNAL_NETWORKS,))


def test_a_missing_setting_is_written_on_rerun():
    _run("DELETE FROM app_settings WHERE setting_key = 'internal_networks'")
    _run("DELETE FROM db_version WHERE version = 20")
    init_db(config.DB_CONFIG)
    assert _setting() == DEFAULT_INTERNAL_NETWORKS
