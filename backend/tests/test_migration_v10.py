"""access_log, task_queue, the internal_networks default (S013 § 4) — built by v10, then by v20
(S025: v1–v13 squashed), now by v41 (S088: v20–v41 squashed).  A test of today's schema on the
test DB.  The re-runs of the squashed entry (a stored value kept, a missing setting written) are
test_migration_squash_v41.py's: on the kept test DB a deleted db_version row is now refused
(S088 § 5.2).
"""

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
    return {r["COLUMN_NAME"]: (r["COLUMN_TYPE"], r["IS_NULLABLE"]) for r in _run(
        "SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s", (table,))}


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
